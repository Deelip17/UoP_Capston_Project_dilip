"""Unit tests for domain records (data dictionary: docs/architecture/05_DATA_FLOW.md section 4)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError

from aitaf.core.models import (
    AnalyzedRequirement,
    ReviewStatus,
    RiskLevel,
    TestCase,
)


def _req(**overrides: Any) -> AnalyzedRequirement:
    data: dict[str, Any] = {
        "req_id": "REQ-001",
        "source_ref": "reqs.md#1",
        "content_hash": "abc123",
        "actors": ["user"],
        "actions": ["login"],
        "preconditions": ["account exists"],
        "outcomes": ["session started"],
        "risk": RiskLevel.MEDIUM,
        "risk_rationale": "Standard login path",
        "prompt_version": "req-analyzer/v1",
    }
    data.update(overrides)
    return AnalyzedRequirement(**data)


def _tc(**overrides: Any) -> TestCase:
    data: dict[str, Any] = {
        "tc_id": "TC-001",
        "req_id": "REQ-001",
        "scenario_id": "SCEN-001",
        "title": "User logs in with valid credentials",
        "preconditions": ["account exists"],
        "steps": ["open login page", "enter valid credentials", "submit"],
        "expected": ["session established"],
        "priority": "M",
    }
    data.update(overrides)
    return TestCase(**data)


@pytest.mark.blackbox
def test_analyzed_requirement_round_trip() -> None:
    r = _req()
    assert r.req_id == "REQ-001"
    assert r.risk is RiskLevel.MEDIUM
    assert r.ai_label == "ai-generated"


@pytest.mark.blackbox
def test_analyzed_requirement_is_frozen() -> None:
    r = _req()
    with pytest.raises(PydanticValidationError):
        r.req_id = "REQ-999"  # type: ignore[misc]


@pytest.mark.blackbox
def test_analyzed_requirement_rejects_extra_fields() -> None:
    """extra='forbid' guards against silent schema drift."""
    with pytest.raises(PydanticValidationError):
        AnalyzedRequirement(
            req_id="REQ-001",
            source_ref="r.md",
            content_hash="h",
            risk=RiskLevel.LOW,
            risk_rationale="r",
            prompt_version="v1",
            unexpected_field="noise",  # type: ignore[call-arg]
        )


@pytest.mark.whitebox
def test_req_id_rejects_whitespace() -> None:
    with pytest.raises(PydanticValidationError):
        _req(req_id="REQ 001")


@pytest.mark.whitebox
def test_req_id_rejects_empty_string() -> None:
    with pytest.raises(PydanticValidationError):
        _req(req_id="")


@pytest.mark.blackbox
def test_test_case_defaults_to_pending_review() -> None:
    """Human-review gate state is Pending until explicitly approved (FR-10)."""
    tc = _tc()
    assert tc.review_status is ReviewStatus.PENDING


@pytest.mark.whitebox
def test_test_case_requires_at_least_one_step() -> None:
    with pytest.raises(PydanticValidationError):
        _tc(steps=[])


@pytest.mark.whitebox
def test_test_case_priority_rejects_invalid_value() -> None:
    with pytest.raises(PydanticValidationError):
        _tc(priority="X")
