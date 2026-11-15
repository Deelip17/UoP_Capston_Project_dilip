"""Failure Analyzer: one analysis per failed or errored test (FR-27 to FR-30).

Steps, cheapest first: the deterministic rules decide the clear cases; an ambiguous
failure is shown to the model only if it is safe (masked, no injection) and the
gateway is available; any problem with the model, including a reached call cap,
degrades to a labelled ``fallback`` analysis instead of an error. Failures with the
same normalised signature share a cluster ID. Every analysis names its evidence and
carries a confidence between 0 and 1; an answer from the model names the model and
the prompt version (NFR-30) and its confidence is capped below certainty.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from aitaf.core.errors import AitafError, LlmValidationError
from aitaf.core.llm import LlmGateway, LlmRequest
from aitaf.core.logging import get_logger
from aitaf.core.masking import mask, validate_llm_json
from aitaf.core.metrics import Metrics, timed
from aitaf.core.models import FailureAnalysis, HealingEvent, TestResult
from aitaf.core.storage import Repository
from aitaf.diagnosis import prompt as fa_prompt
from aitaf.diagnosis.rules import FailureFacts, Verdict, classify
from aitaf.diagnosis.signature import cluster_id

_log = get_logger(__name__)
MODEL_CONFIDENCE_CAP = 0.8
FALLBACK_CONFIDENCE = 0.3
_FAILED = ("failed", "error")


@dataclass
class AnalysisResult:
    """All analyses of one run, the clusters they form and the model calls made."""

    analyses: list[FailureAnalysis] = field(default_factory=list)
    clusters: dict[str, list[str]] = field(default_factory=dict)
    llm_calls: int = 0

    @property
    def by_category(self) -> Counter[str]:
        return Counter(a.category for a in self.analyses)


class FailureAnalyzer:
    """Classify and explain the failed tests of a stored run."""

    def __init__(
        self,
        gateway: LlmGateway | None,
        repo: Repository,
        metrics: Metrics | None = None,
        evidence_dir: Path | None = None,
    ) -> None:
        self._gateway = gateway
        self._repo = repo
        self._metrics = metrics
        self._evidence_dir = evidence_dir
        self._calls = 0

    def analyze(self, run_id: str) -> AnalysisResult:
        outcome = AnalysisResult()
        self._calls = 0
        failures = [r for r in self._repo.list_results(run_id) if r.status in _FAILED]
        events = self._repo.list_healing_events(run_id)
        with timed(self._metrics, "failure_analyzer", "analyze"):
            for result in failures:
                analysis = self._analyse_one(run_id, result, _events_for(result, events))
                self._repo.add_failure_analysis(run_id, analysis)
                outcome.analyses.append(analysis)
                outcome.clusters.setdefault(analysis.cluster_id, []).append(analysis.tc_id)
        outcome.llm_calls = self._calls
        return outcome

    # ------------------------------------------------------------------- steps

    def _analyse_one(
        self, run_id: str, result: TestResult, events: list[HealingEvent]
    ) -> FailureAnalysis:
        facts = FailureFacts(
            status=result.status,
            error_type=result.error_type,
            error_text=result.error_text,
            log=result.log,
            attempts=result.attempts,
            healing_outcomes=tuple(e.outcome for e in events),
        )
        verdict = classify(facts)
        source = "rules"
        model: str | None = None
        version: str | None = None
        if verdict is None:
            verdict, model = self._ask_model(result, facts, events)
            if model is not None:
                source, version = "llm", fa_prompt.PROMPT_VERSION
            else:
                source = "fallback"
        refs = [f"log:{result.result_id}"]
        if result.screenshot:
            refs.append(f"screenshot:{result.screenshot}")
        if result.dom_snapshot:
            refs.append(f"dom:{result.dom_snapshot}")
        refs += [f"healing:{event.event_id}" for event in events]
        return FailureAnalysis(
            analysis_id=f"FA-{result.result_id}",
            run_id=run_id,
            result_id=result.result_id,
            tc_id=result.tc_id,
            category=verdict.category,
            root_cause=verdict.cause,
            remediation=verdict.remediation,
            evidence_refs=refs,
            confidence=verdict.confidence,
            cluster_id=cluster_id(result.error_type, result.error_text),
            source=source,  # type: ignore[arg-type]
            model=model,
            prompt_version=version,
            created_at=datetime.now(UTC),
        )

    def _ask_model(
        self, result: TestResult, facts: FailureFacts, events: list[HealingEvent]
    ) -> tuple[Verdict, str | None]:
        """Ask the model about an ambiguous failure; return (verdict, model name or None)."""
        if self._gateway is None:
            return _fallback(result, "no AI explanation was requested"), None
        fields = {
            "tc_id": result.tc_id,
            "status": result.status,
            "attempts": str(result.attempts),
            "error_type": result.error_type or "unknown",
            "error_text": result.error_text,
            "log": result.log,
            "healing": ", ".join(f"{e.strategy_used}:{e.outcome}" for e in events) or "none",
            "dom_text": self._dom_text(result.dom_snapshot),
            "screenshot": result.screenshot,
        }
        text = fa_prompt.build_prompt(**fields)
        if text is None:
            return (
                _fallback(
                    result,
                    "its text looks like a prompt injection, so it was not sent to the model",
                ),
                None,
            )
        reason = "the AI explanation was unavailable"
        for attempt in range(2):
            try:
                self._calls += 1
                response = self._gateway.complete(
                    LlmRequest(
                        component=fa_prompt.COMPONENT,
                        prompt_version=fa_prompt.PROMPT_VERSION,
                        prompt=text,
                    )
                )
                answer = validate_llm_json(response.text, fa_prompt.AnalysisSchema)
            except LlmValidationError as exc:
                _log.warning("failure analysis answer invalid (attempt %d): %s", attempt + 1, exc)
                reason = "the AI explanation did not match the required format"
                reasked = fa_prompt.build_reask_prompt(reason=str(exc), **fields)
                text = reasked if reasked is not None else text
                continue
            except AitafError as exc:
                _log.warning("failure analysis model unavailable: %s", exc)
                return _fallback(result, "the AI explanation was unavailable"), None
            return (
                Verdict(
                    answer.category,
                    min(answer.confidence, MODEL_CONFIDENCE_CAP),
                    "model",
                    answer.root_cause,
                    answer.remediation,
                ),
                response.model,
            )
        return _fallback(result, reason), None

    def _dom_text(self, name: str) -> str:
        """Visible text of the failing page, read only from inside the evidence directory."""
        if not name or self._evidence_dir is None or Path(name).name != name:
            return ""
        try:
            page = (self._evidence_dir / name).read_text(encoding="utf-8")
        except OSError:
            return ""
        return fa_prompt.dom_text_snippet(page)


def _events_for(result: TestResult, events: list[HealingEvent]) -> list[HealingEvent]:
    if not result.nodeid:
        return []
    return [e for e in events if e.step_ref.startswith(result.nodeid + "#")]


def _fallback(result: TestResult, why: str) -> Verdict:
    kind = result.error_type or "no exception type"
    cause = mask(f"No rule matched this failure ({kind}) and {why}.").text
    return Verdict(
        "unknown",
        FALLBACK_CONFIDENCE,
        "fallback",
        cause,
        "Open the screenshot and the log, reproduce the failure by hand and classify it.",
    )
