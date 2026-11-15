"""Requirement Analyzer (FR-02 to FR-05, FR-30, NFR-10, NFR-13, NFR-17).

Pipeline per requirement: sanitise (fail closed) -> mask -> LLM extraction via
the gateway -> schema validation (one re-ask) -> deterministic ID -> combined
risk rating -> ambiguity flags -> persist. Requirements that fail validation are
reported as rejected and never reach the LLM; ambiguous ones are flagged and
excluded from generation until clarified.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from aitaf.analyzer.intake import RawRequirement
from aitaf.analyzer.prompts import PROMPT_VERSION, build_prompt, build_reask_prompt
from aitaf.core.errors import LlmValidationError, ValidationError
from aitaf.core.llm import LlmGateway, LlmRequest
from aitaf.core.logging import current_run_id, get_logger
from aitaf.core.masking import mask, sanitize_requirement_text, validate_llm_json
from aitaf.core.models import AnalyzedRequirement, RiskLevel
from aitaf.core.storage import Repository

COMPONENT = "requirement_analyzer"

_log = get_logger(__name__)

_RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
_HIGH = re.compile(
    r"\b(pay\w*|credit|checkout|order\w*|refund\w*|password\w*|log ?in|authenticat\w*|"
    r"authoris\w*|authoriz\w*|admin\w*|delete\w*|personal|security|account)\b",
    re.IGNORECASE,
)
_MEDIUM = re.compile(
    r"\b(search\w*|cart|update\w*|profile|edit\w*|filter\w*|list|upload\w*|download\w*)\b",
    re.IGNORECASE,
)
_VAGUE = re.compile(
    r"\b(quick(?:ly)?|fast|easy|easily|user-friendly|intuitive|appropriate(?:ly)?|adequate|"
    r"reasonabl[ey]|flexible|robust|efficient(?:ly)?|as needed|etc|and/or)\b",
    re.IGNORECASE,
)


class ExtractionSchema(BaseModel):
    """Fixed JSON schema the model must return (FR-03, NFR-10)."""

    model_config = ConfigDict(extra="forbid")

    actors: list[str]
    actions: list[str] = Field(min_length=1)
    preconditions: list[str]
    outcomes: list[str]
    risk: RiskLevel
    risk_rationale: str = Field(min_length=1)
    ambiguities: list[str] = Field(default_factory=list)


@dataclass
class AnalysisResult:
    """Outcome of one analysis pass."""

    ready: list[AnalyzedRequirement] = field(default_factory=list)
    flagged: list[AnalyzedRequirement] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)


def _rule_risk(text: str) -> tuple[RiskLevel, list[str]]:
    high = sorted({m.lower() for m in _HIGH.findall(text)})
    if high:
        return RiskLevel.HIGH, high
    medium = sorted({m.lower() for m in _MEDIUM.findall(text)})
    if medium:
        return RiskLevel.MEDIUM, medium
    return RiskLevel.LOW, []


def _ambiguity_flags(text: str, extraction: ExtractionSchema) -> list[str]:
    flags = [f"vague wording: '{w.lower()}'" for w in dict.fromkeys(_VAGUE.findall(text))]
    lowered = text.lower()
    if re.search(r"\balways\b", lowered) and re.search(r"\bnever\b", lowered):
        flags.append("possible contradiction: both 'always' and 'never'")
    if not extraction.outcomes:
        flags.append("no expected outcome stated")
    flags.extend(extraction.ambiguities)
    return flags


class RequirementAnalyzer:
    """Turns raw requirements into structured, risk-rated records."""

    def __init__(self, gateway: LlmGateway, repo: Repository) -> None:
        self._gateway = gateway
        self._repo = repo

    def analyze(self, items: list[RawRequirement]) -> AnalysisResult:
        result = AnalysisResult()
        for item in items:
            try:
                clean = sanitize_requirement_text(item.text, source=item.source_ref)
            except ValidationError as exc:
                result.rejected.append((item.source_ref, str(exc)))
                continue
            record = self._analyze_one(item.source_ref, clean)
            self._repo.add_requirement(current_run_id(), record)
            (result.flagged if record.ambiguity_flags else result.ready).append(record)
        return result

    def _extract(self, masked: str) -> ExtractionSchema:
        prompt = build_prompt(masked)
        for attempt in range(2):
            response = self._gateway.complete(
                LlmRequest(component=COMPONENT, prompt_version=PROMPT_VERSION, prompt=prompt)
            )
            try:
                return validate_llm_json(response.text, ExtractionSchema)
            except LlmValidationError as exc:
                _log.warning("extraction output invalid (attempt %d): %s", attempt + 1, exc)
                if attempt == 1:
                    raise
                prompt = build_reask_prompt(masked, str(exc))
        raise AssertionError("unreachable")  # pragma: no cover

    def _analyze_one(self, source_ref: str, clean: str) -> AnalyzedRequirement:
        masked = mask(clean).text
        extraction = self._extract(masked)
        content_hash = hashlib.sha256(clean.encode("utf-8")).hexdigest()
        req_id = (
            "REQ-" + hashlib.sha256(f"{source_ref}:{content_hash}".encode()).hexdigest()[:8].upper()
        )

        rule_level, matched = _rule_risk(masked)
        final = max(extraction.risk, rule_level, key=_RISK_ORDER.__getitem__)
        rationale = extraction.risk_rationale.strip()
        if matched:
            rationale += f" Keyword rules rated {rule_level.value} ({', '.join(matched)})."
        rationale += f" Final rating: {final.value}."

        return AnalyzedRequirement(
            req_id=req_id,
            source_ref=source_ref,
            content_hash=content_hash,
            actors=extraction.actors,
            actions=extraction.actions,
            preconditions=extraction.preconditions,
            outcomes=extraction.outcomes,
            risk=final,
            risk_rationale=rationale,
            ambiguity_flags=_ambiguity_flags(masked, extraction),
            prompt_version=PROMPT_VERSION,
        )
