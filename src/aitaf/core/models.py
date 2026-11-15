"""Domain records exchanged between modules.

Data dictionary: ``docs/architecture/05_DATA_FLOW.md`` section 4. Each record
is a pydantic model: immutable (``frozen=True``), rejects unknown fields
(``extra="forbid"``) and carries the IDs needed for end-to-end traceability
(FR-34). AI-generated records are labelled so no downstream step can confuse
them with human-authored artefacts (NFR-30).

Later slices add further records (``TestScenario``, ``TestData``, ``Script``,
``Locator``, ``Artifact``, ``HealingEvent``, ``FailureAnalysis``). So far:
``AnalyzedRequirement`` and ``TestCase`` (slice 1), ``Run``, ``TestResult`` and
``LlmAudit`` (slice 2), ``TestScenario`` and ``TestData`` (slice 4).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    """Outcome, duration and log of one executed test (FR-19, FR-34)."""

    __test__: ClassVar[bool] = False

    result_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    tc_id: str = Field(min_length=1)
    status: Literal["passed", "failed", "skipped", "error"]
    duration_ms: int = Field(ge=0)
    log: str = ""


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
