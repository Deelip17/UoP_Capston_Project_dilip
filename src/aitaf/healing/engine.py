"""Self-Healing Engine (FR-22 to FR-26, FR-30, NFR-03, NFR-13).

Cost-ordered repair ladder for a failed step: classify the failure, then try the
stored fallback locators, then DOM-similarity matching, then (only if enabled and
a gateway is configured) an LLM suggestion. Every candidate is validated before
it is accepted, every attempt is recorded as a proposed, unapproved
``HealingEvent``, and attempts are bounded per step and per run. A permanent
change to the locator repository is a separate, human-approved action
(``aitaf.healing.approval``).
"""

from __future__ import annotations

import time
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from aitaf.core.errors import AitafError, LlmValidationError, PolicyError, ValidationError
from aitaf.core.healing import (
    ElementSignature,
    FailureContext,
    FailureKind,
    HealResult,
    HealStatus,
)
from aitaf.core.llm import LlmGateway, LlmRequest
from aitaf.core.logging import current_run_id, get_logger
from aitaf.core.masking import validate_llm_json
from aitaf.core.metrics import Metrics, timed
from aitaf.core.models import HealingEvent, LocatorStrategy
from aitaf.core.storage import Repository
from aitaf.healing import llm_step
from aitaf.healing.classify import classify_failure
from aitaf.healing.dom import Dom, DomElement, parse_dom
from aitaf.healing.locators import resolves_uniquely, unique_strategy_for
from aitaf.healing.resolver import find_elements
from aitaf.healing.signature import signature_from_locator
from aitaf.healing.similarity import rank, similarity
from aitaf.healing.validate import validate_candidate

_log = get_logger(__name__)
Rung = Literal["fallback", "similarity", "llm"]


@dataclass(frozen=True)
class HealingConfig:
    """Limits and thresholds (FR-26); the LLM rung is off unless enabled (ADR-026)."""

    max_attempts_per_step: int = 3
    max_attempts_per_run: int = 20
    similarity_threshold: float = 0.6
    top_candidates: int = 3
    llm_enabled: bool = False
    llm_candidates: int = 15


@dataclass
class _Candidate:
    strategy: LocatorStrategy | None
    element: DomElement
    confidence: float
    model: str | None = None
    prompt_version: str | None = None


@dataclass
class _Found:
    candidates: list[_Candidate]
    note: str = ""


class SelfHealingEngine:
    """Repairs broken locators during execution without hiding real defects."""

    def __init__(
        self,
        repo: Repository,
        config: HealingConfig | None = None,
        gateway: LlmGateway | None = None,
        metrics: Metrics | None = None,
    ) -> None:
        self._repo = repo
        self._config = config or HealingConfig()
        self._gateway = gateway
        self._metrics = metrics
        self._step_attempts: Counter[str] = Counter()
        self._run_attempts = 0

    def heal(self, ctx: FailureContext) -> HealResult:
        with timed(self._metrics, "self_healing", "heal") as probe:
            result = self._heal(ctx)
            probe.detail = result.status.value
            return result

    def _heal(self, ctx: FailureContext) -> HealResult:
        run_id = current_run_id()
        if not run_id:
            raise PolicyError("no run ID is set; start a run before healing")
        kind = classify_failure(ctx.error_type, ctx.error_message)
        if kind is not FailureKind.LOCATOR:
            reason = f"{kind.value.replace('_', ' ')} failures are never repaired"
            return HealResult(HealStatus.NOT_HEALABLE, kind, reason=reason)
        if (
            self._step_attempts[ctx.step_ref] >= self._config.max_attempts_per_step
            or self._run_attempts >= self._config.max_attempts_per_run
        ):
            return HealResult(
                HealStatus.LIMIT_REACHED, kind, reason="healing attempt limit reached"
            )
        self._step_attempts[ctx.step_ref] += 1
        self._run_attempts += 1
        try:
            dom = parse_dom(ctx.dom_html)
        except ValidationError as exc:
            return HealResult(HealStatus.NOT_HEALED, kind, reason=f"DOM snapshot rejected: {exc}")

        started = time.perf_counter()
        expected = ctx.baseline or signature_from_locator(ctx.locator)
        events: list[HealingEvent] = []
        accepted: HealingEvent | None = None
        for rung, produce in self._ladder(ctx, dom, expected):
            found = produce()
            if not found.candidates:
                events.append(self._event(ctx, run_id, rung, started, note=found.note))
                continue
            for candidate in found.candidates:
                event = self._judge(ctx, run_id, rung, started, dom, expected, candidate)
                events.append(event)
                if event.outcome == "proposed":
                    accepted = event
                    break
            if accepted:
                break

        for event in events:
            self._repo.add_healing_event(run_id, event)
        if accepted is None:
            return HealResult(
                HealStatus.NOT_HEALED,
                kind,
                events=events,
                reason="no candidate passed validation; the step still fails",
            )
        return HealResult(
            HealStatus.HEALED,
            kind,
            strategy=accepted.new_strategy,
            confidence=accepted.confidence,
            events=events,
        )

    def _ladder(
        self, ctx: FailureContext, dom: Dom, expected: ElementSignature
    ) -> list[tuple[Rung, Callable[[], _Found]]]:
        ladder: list[tuple[Rung, Callable[[], _Found]]] = [
            ("fallback", lambda: self._fallbacks(ctx, dom, expected)),
            ("similarity", lambda: self._similar(dom, expected)),
        ]
        if self._config.llm_enabled and self._gateway is not None:
            ladder.append(("llm", lambda: self._suggest(ctx, dom, expected)))
        return ladder

    def _fallbacks(self, ctx: FailureContext, dom: Dom, expected: ElementSignature) -> _Found:
        candidates: list[_Candidate] = []
        for strategy in ctx.locator.fallbacks:
            matches = find_elements(dom, strategy)
            if not matches:
                continue
            best = max(matches, key=lambda e: (similarity(expected, dom, e), -e.index))
            candidates.append(_Candidate(strategy, best, similarity(expected, dom, best)))
        return _Found(candidates, "no stored fallback locator matched an element")

    def _similar(self, dom: Dom, expected: ElementSignature) -> _Found:
        threshold = self._config.similarity_threshold
        ranked = [(s, e) for s, e in rank(expected, dom) if s >= threshold]
        candidates = [_Candidate(None, e, s) for s, e in ranked[: self._config.top_candidates]]
        return _Found(candidates, f"no element reached the similarity threshold {threshold}")

    def _suggest(self, ctx: FailureContext, dom: Dom, expected: ElementSignature) -> _Found:
        assert self._gateway is not None
        shown = [e for _, e in rank(expected, dom)[: self._config.llm_candidates]]
        intent = llm_step.render_intent(ctx.action, ctx.locator.name, expected)
        fragment = llm_step.render_fragment(shown)
        prompt = llm_step.build_prompt(intent, fragment)
        suggestion = None
        model = ""
        try:
            for attempt in range(2):
                response = self._gateway.complete(
                    LlmRequest(
                        component=llm_step.COMPONENT,
                        prompt_version=llm_step.PROMPT_VERSION,
                        prompt=prompt,
                    )
                )
                try:
                    suggestion = validate_llm_json(response.text, llm_step.SuggestionSchema)
                    model = response.model
                    break
                except LlmValidationError as exc:
                    _log.warning("healing suggestion invalid (attempt %d): %s", attempt + 1, exc)
                    prompt = llm_step.build_reask_prompt(intent, fragment, str(exc))
        except AitafError as exc:
            _log.warning("LLM healing step unavailable: %s", exc)
            return _Found([], "LLM step unavailable")
        if suggestion is None:
            return _Found([], "LLM output did not match the schema")
        strategy = LocatorStrategy(kind=suggestion.strategy.kind, value=suggestion.strategy.value)
        matches = find_elements(dom, strategy)
        if not matches:
            return _Found([], "the suggested locator matches no element")
        best = max(matches, key=lambda e: (similarity(expected, dom, e), -e.index))
        candidate = _Candidate(
            strategy, best, suggestion.confidence, model, llm_step.PROMPT_VERSION
        )
        return _Found([candidate])

    def _judge(
        self,
        ctx: FailureContext,
        run_id: str,
        rung: Rung,
        started: float,
        dom: Dom,
        expected: ElementSignature,
        candidate: _Candidate,
    ) -> HealingEvent:
        verdict = validate_candidate(expected, dom, candidate.element, ctx.action)
        reasons = list(verdict.reasons)
        if candidate.strategy is not None and resolves_uniquely(
            dom, candidate.strategy, candidate.element
        ):
            new_strategy: LocatorStrategy | None = candidate.strategy
        else:
            new_strategy = unique_strategy_for(dom, candidate.element)
        if verdict.passed and new_strategy is None:
            reasons.append("no unique locator derivable for the candidate")
        passed = verdict.passed and new_strategy is not None
        return self._event(
            ctx,
            run_id,
            rung,
            started,
            outcome="proposed" if passed else "rejected",
            new_strategy=new_strategy,
            confidence=candidate.confidence,
            validated=passed,
            note="; ".join(reasons),
            model=candidate.model,
            prompt_version=candidate.prompt_version,
        )

    def _event(
        self,
        ctx: FailureContext,
        run_id: str,
        rung: Rung,
        started: float,
        *,
        outcome: Literal["proposed", "rejected", "no_candidate"] = "no_candidate",
        new_strategy: LocatorStrategy | None = None,
        confidence: float = 0.0,
        validated: bool = False,
        note: str = "",
        model: str | None = None,
        prompt_version: str | None = None,
    ) -> HealingEvent:
        return HealingEvent(
            event_id=uuid.uuid4().hex,
            run_id=run_id,
            step_ref=ctx.step_ref,
            loc_id=ctx.locator.loc_id,
            old_strategy=ctx.locator.primary,
            new_strategy=new_strategy,
            strategy_used=rung,
            confidence=round(min(1.0, max(0.0, confidence)), 4),
            validated=validated,
            outcome=outcome,
            reason=note,
            duration_ms=int((time.perf_counter() - started) * 1000),
            model=model,
            prompt_version=prompt_version,
            created_at=datetime.now(UTC),
        )
