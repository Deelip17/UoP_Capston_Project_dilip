"""Domain records exchanged between modules.

Data dictionary: ``docs/architecture/05_DATA_FLOW.md`` section 4. Each record
is a pydantic model: immutable (``frozen=True``), rejects unknown fields
(``extra="forbid"``) and carries the IDs needed for end-to-end traceability
(FR-34). AI-generated records are labelled so no downstream step can confuse
them with human-authored artefacts (NFR-30).

Later slices add further records (``TestScenario``, ``TestData``, ``Script``,
``Locator``, ``Artifact``, ``HealingEvent``, ``FailureAnalysis``). So far:
``AnalyzedRequirement`` and ``TestCase`` (slice 1), ``Run``, ``TestResult`` and
``LlmAudit`` (slice 2), ``TestScenario`` and ``TestData`` (slice 4), ``Script``, ``Locator`` and
``LocatorStrategy`` (slice 5), ``HealingEvent`` (slice 6), ``MetricSample`` (slice 7).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RiskLevel(StrEnum):
    """Risk rating produced by the Requirement Analyzer (FR-04)."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ReviewStatus(StrEnum):
    """Human-review state at the test-case approval gate (FR-10)."""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class RunStatus(StrEnum):
    """Lifecycle of a pipeline run; INCOMPLETE marks an interrupted run (NFR-07)."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


class _BaseRecord(BaseModel):
    """Shared configuration for every domain record."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class AnalyzedRequirement(_BaseRecord):
    """Structured requirement produced by the Requirement Analyzer.

    Requirements: FR-01 to FR-05 (intake, validation, extraction, ID and risk,
    ambiguity flags), FR-34 (traceability), NFR-22 (versioned prompts),
    NFR-30 (AI-generated label).
    """

    req_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    actors: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    risk: RiskLevel
    risk_rationale: str = Field(min_length=1)
    ambiguity_flags: list[str] = Field(default_factory=list)
    prompt_version: str = Field(min_length=1)
    ai_label: Literal["ai-generated"] = "ai-generated"

    @field_validator("req_id")
    @classmethod
    def _req_id_without_whitespace(cls, value: str) -> str:
        if any(c.isspace() for c in value):
            raise ValueError("req_id must not contain whitespace")
        return value


class TestCase(_BaseRecord):
    """Test case derived from an analysed requirement (FR-06 to FR-10, FR-34)."""

    # Tell pytest not to collect this class as a test container (it starts with "Test").
    __test__: ClassVar[bool] = False

    tc_id: str = Field(min_length=1)
    req_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1)
    expected: list[str] = Field(min_length=1)
    priority: Literal["M", "S", "C"]
    review_status: ReviewStatus = ReviewStatus.PENDING
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    ai_label: Literal["ai-generated"] = "ai-generated"


class Run(_BaseRecord):
    """One pipeline run with its environment, for traceability (FR-19, FR-34, NFR-07)."""

    run_id: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime | None = None
    status: RunStatus
    provider: str = Field(min_length=1)
    environment: str = Field(min_length=1)


class TestResult(_BaseRecord):
    """Outcome, duration, log and evidence links of one executed test (FR-18, FR-19, FR-20, FR-34).

    ``attempts`` counts the runs of the test including retries; ``screenshot`` and
    ``dom_snapshot`` are file names relative to the run's evidence directory.
    """

    __test__: ClassVar[bool] = False

    result_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    tc_id: str = Field(min_length=1)
    status: Literal["passed", "failed", "skipped", "error"]
    duration_ms: int = Field(ge=0)
    log: str = ""
    attempts: int = Field(default=1, ge=1)
    screenshot: str = ""
    dom_snapshot: str = ""


class LlmAudit(_BaseRecord):
    """Audit record for one LLM call (FR-37, NFR-14).

    There is deliberately no field for the prompt text or any credential: only a
    hash of the input is kept, so the audit table cannot leak either.
    """

    call_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    component: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    input_hash: str = Field(min_length=64, max_length=64)
    status: Literal["ok", "fallback", "error"]
    mock: bool
    created_at: datetime


class TestScenario(_BaseRecord):
    """Positive, negative or boundary scenario for a requirement (FR-06, FR-34, NFR-30)."""

    __test__: ClassVar[bool] = False

    scenario_id: str = Field(min_length=1)
    req_id: str = Field(min_length=1)
    scenario_type: Literal["positive", "negative", "boundary"]
    description: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    ai_label: Literal["ai-generated"] = "ai-generated"


class TestData(_BaseRecord):
    """Synthetic data for one test case; real personal data is never allowed (FR-08)."""

    __test__: ClassVar[bool] = False

    tc_id: str = Field(min_length=1)
    dataset: dict[str, str]
    synthetic: Literal[True] = True


class LocatorStrategy(_BaseRecord):
    """One way of finding an element: id, CSS, XPath, text, role or attribute (FR-16)."""

    kind: Literal["id", "css", "xpath", "text", "role", "attr"]
    value: str = Field(min_length=1)


class Locator(_BaseRecord):
    """Named element locator with a primary and ordered fallback strategies (FR-14, FR-16)."""

    loc_id: str = Field(min_length=1)
    page: str = Field(min_length=1)
    name: str = Field(min_length=1)
    primary: LocatorStrategy
    fallbacks: list[LocatorStrategy] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    ai_label: Literal["ai-generated"] = "ai-generated"


class Script(_BaseRecord):
    """Manifest entry for one generated, statically validated script (FR-12 to FR-15)."""

    script_id: str = Field(min_length=1)
    tc_id: str = Field(min_length=1)
    framework: Literal["playwright", "selenium"]
    path: str = Field(min_length=1)
    validation_result: Literal["passed"]
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    ai_label: Literal["ai-generated"] = "ai-generated"


class HealingEvent(_BaseRecord):
    """One healing attempt: old and new locator, strategy, confidence, outcome (FR-23 to FR-25).

    Events start unapproved. Only a validated, proposed event can be approved, and
    only an approved event may change the locator repository permanently.
    """

    event_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    step_ref: str = Field(min_length=1)
    loc_id: str = Field(min_length=1)
    old_strategy: LocatorStrategy
    new_strategy: LocatorStrategy | None = None
    strategy_used: Literal["fallback", "similarity", "llm"]
    confidence: float = Field(ge=0.0, le=1.0)
    validated: bool
    outcome: Literal["proposed", "rejected", "no_candidate"]
    approved: bool = False
    reason: str = ""
    duration_ms: int = Field(ge=0)
    model: str | None = None
    prompt_version: str | None = None
    created_at: datetime

    @model_validator(mode="after")
    def _outcome_is_consistent(self) -> HealingEvent:
        if self.outcome == "proposed":
            if self.new_strategy is None or not self.validated:
                raise ValueError("a proposed event needs a new locator and must be validated")
        elif self.validated:
            raise ValueError("only a proposed event can be validated")
        if self.approved and self.outcome != "proposed":
            raise ValueError("only a proposed event can be approved")
        return self


class MetricSample(_BaseRecord):
    """One timed operation: latency, outcome, tokens and cost (NFR-35, FR-33)."""

    run_id: str = Field(min_length=1)
    component: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    outcome: Literal["ok", "error"]
    detail: str = ""
    duration_ms: float = Field(ge=0.0)
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    created_at: datetime
