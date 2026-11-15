"""Test Case Generator (FR-05 to FR-10, FR-30, NFR-10, NFR-13, NFR-17, NFR-30, NFR-32).

Per eligible requirement: mask -> one LLM call that returns scenarios, cases and
suggested data -> schema validation (one re-ask) -> labelled records with
deterministic IDs -> synthetic-data check. After all requirements: near-duplicate
removal, coverage review, persistence. Ambiguous requirements are skipped until
clarified; new cases are Pending human review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aitaf.core.errors import LlmValidationError
from aitaf.core.llm import LlmGateway, LlmRequest
from aitaf.core.logging import current_run_id, get_logger
from aitaf.core.masking import find_injection, mask, validate_llm_json
from aitaf.core.metrics import Metrics, timed
from aitaf.core.models import AnalyzedRequirement, TestCase, TestData, TestScenario
from aitaf.core.storage import Repository
from aitaf.generator.prompts import PROMPT_VERSION, build_prompt, build_reask_prompt
from aitaf.generator.synthetic import is_synthetic_safe, rule_value

COMPONENT = "test_case_generator"
DUPLICATE_THRESHOLD = 0.95

_log = get_logger(__name__)
_KINDS = {"positive", "negative", "boundary"}


class CaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1)
    expected: list[str] = Field(min_length=1)
    priority: Literal["M", "S", "C"]
    data: dict[str, str] = Field(default_factory=dict)


class ScenarioSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["positive", "negative", "boundary"]
    description: str = Field(min_length=1)
    cases: list[CaseSchema] = Field(min_length=1)


class GenerationSchema(BaseModel):
    """Fixed JSON schema the model must return (FR-06, FR-07, NFR-10)."""

    model_config = ConfigDict(extra="forbid")

    scenarios: list[ScenarioSchema] = Field(min_length=1)

    @model_validator(mode="after")
    def _every_kind_present(self) -> GenerationSchema:
        missing = _KINDS - {s.kind for s in self.scenarios}
        if missing:
            raise ValueError(f"missing scenario kinds: {sorted(missing)}")
        return self


@dataclass
class GenerationResult:
    """Outcome of one generation pass."""

    scenarios: list[TestScenario] = field(default_factory=list)
    cases: list[TestCase] = field(default_factory=list)
    test_data: list[TestData] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    duplicates_removed: int = 0
    data_replaced: int = 0
    coverage_gaps: list[str] = field(default_factory=list)


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _record(req: AnalyzedRequirement) -> str:
    return "\n".join(
        [
            f"Requirement ID: {req.req_id}",
            f"Actors: {_one_line('; '.join(req.actors))}",
            f"Actions: {_one_line('; '.join(req.actions))}",
            f"Preconditions: {_one_line('; '.join(req.preconditions))}",
            f"Outcomes: {_one_line('; '.join(req.outcomes))}",
            f"Risk: {req.risk.value}",
        ]
    )


def _normalised(case: TestCase) -> str:
    text = " ".join([case.title, *case.steps, *case.expected]).lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text).split())


class TestCaseGenerator:
    """Turns analysed requirements into reviewable test scenarios, cases and data."""

    __test__ = False

    def __init__(
        self, gateway: LlmGateway, repo: Repository, metrics: Metrics | None = None
    ) -> None:
        self._gateway = gateway
        self._repo = repo
        self._metrics = metrics

    def generate(self, requirements: list[AnalyzedRequirement]) -> GenerationResult:
        with timed(self._metrics, COMPONENT, "generate") as probe:
            result = self._generate(requirements)
            probe.detail = f"{len(result.cases)} cases, {result.duplicates_removed} duplicates"
            return result

    def _generate(self, requirements: list[AnalyzedRequirement]) -> GenerationResult:
        result = GenerationResult()
        data_by_case: dict[str, TestData] = {}
        for req in requirements:
            if req.ambiguity_flags:
                result.skipped.append(
                    (req.req_id, "flagged as ambiguous; clarify before generation")
                )
                continue
            record = _record(req)
            matched = find_injection(record)
            if matched:
                reason = f"possible prompt injection ({', '.join(matched)})"
                _log.warning("skipped %s: %s", req.req_id, reason)
                result.skipped.append((req.req_id, reason))
                continue
            schema, model = self._extract(mask(record).text)
            self._build(req, schema, model, result, data_by_case)

        result.cases = self._remove_duplicates(result, data_by_case)
        result.test_data = [data_by_case[c.tc_id] for c in result.cases if c.tc_id in data_by_case]
        result.coverage_gaps = self._coverage_gaps(requirements, result.cases)

        run_id = current_run_id()
        for scenario in result.scenarios:
            self._repo.add_scenario(run_id, scenario)
        for case in result.cases:
            self._repo.add_test_case(run_id, case)
        for data in result.test_data:
            self._repo.add_test_data(run_id, data)
        return result

    def _extract(self, record: str) -> tuple[GenerationSchema, str]:
        prompt = build_prompt(record)
        for attempt in range(2):
            response = self._gateway.complete(
                LlmRequest(component=COMPONENT, prompt_version=PROMPT_VERSION, prompt=prompt)
            )
            try:
                return validate_llm_json(response.text, GenerationSchema), response.model
            except LlmValidationError as exc:
                _log.warning("generation output invalid (attempt %d): %s", attempt + 1, exc)
                if attempt == 1:
                    raise
                prompt = build_reask_prompt(record, str(exc))
        raise AssertionError("unreachable")  # pragma: no cover

    def _build(
        self,
        req: AnalyzedRequirement,
        schema: GenerationSchema,
        model: str,
        result: GenerationResult,
        data_by_case: dict[str, TestData],
    ) -> None:
        suffix = req.req_id.removeprefix("REQ-")
        number = 0
        for s_index, scenario in enumerate(schema.scenarios, start=1):
            scenario_id = f"{req.req_id}-S{s_index}"
            result.scenarios.append(
                TestScenario(
                    scenario_id=scenario_id,
                    req_id=req.req_id,
                    scenario_type=scenario.kind,
                    description=_one_line(scenario.description),
                    model=model,
                    prompt_version=PROMPT_VERSION,
                )
            )
            for item in scenario.cases:
                number += 1
                tc_id = f"TC-{suffix}-{number:02d}"
                result.cases.append(
                    TestCase(
                        tc_id=tc_id,
                        req_id=req.req_id,
                        scenario_id=scenario_id,
                        title=_one_line(item.title),
                        preconditions=[_one_line(p) for p in item.preconditions],
                        steps=[_one_line(s) for s in item.steps],
                        expected=[_one_line(e) for e in item.expected],
                        priority=item.priority,
                        model=model,
                        prompt_version=PROMPT_VERSION,
                    )
                )
                dataset: dict[str, str] = {}
                for key, value in item.data.items():
                    if is_synthetic_safe(value):
                        dataset[key] = value
                    else:
                        dataset[key] = rule_value(key, number)
                        result.data_replaced += 1
                if dataset:
                    data_by_case[tc_id] = TestData(tc_id=tc_id, dataset=dataset)

    def _remove_duplicates(
        self, result: GenerationResult, data_by_case: dict[str, TestData]
    ) -> list[TestCase]:
        kept: list[TestCase] = []
        kept_text: list[str] = []
        for case in result.cases:
            text = _normalised(case)
            if any(
                SequenceMatcher(None, text, other).ratio() >= DUPLICATE_THRESHOLD
                for other in kept_text
            ):
                result.duplicates_removed += 1
                data_by_case.pop(case.tc_id, None)
                continue
            kept.append(case)
            kept_text.append(text)
        return kept

    def _coverage_gaps(
        self, requirements: list[AnalyzedRequirement], cases: list[TestCase]
    ) -> list[str]:
        gaps: list[str] = []
        for req in requirements:
            own = [c for c in cases if c.req_id == req.req_id]
            if not own:
                continue
            text = " ".join(
                " ".join([c.title, *c.preconditions, *c.steps, *c.expected]) for c in own
            ).lower()
            gaps.extend(
                f"{req.req_id}: role '{actor}' is not represented in any test case"
                for actor in req.actors
                if actor.lower() not in text
            )
        return gaps
