"""Human review gate tests.

Requirements: FR-10 (Pending/Approved/Rejected; in review mode only Approved
cases are scripted; status changes are logged), NFR-31 (no unapproved change
reaches the next stage).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from aitaf.core.errors import PersistenceError
from aitaf.core.logging import set_run_id
from aitaf.core.models import ReviewStatus, Run, RunStatus, TestCase
from aitaf.core.storage import InMemoryRepository
from aitaf.generator import cases_for_scripting, set_review_status


def make_case(tc_id: str) -> TestCase:
    return TestCase(
        tc_id=tc_id,
        req_id="REQ-1",
        scenario_id="REQ-1-S1",
        title=f"case {tc_id}",
        steps=["a"],
        expected=["b"],
        priority="M",
        model="mock-1",
        prompt_version="tg-v1",
    )


@pytest.fixture
def repo() -> Iterator[InMemoryRepository]:
    repository = InMemoryRepository()
    repository.create_run(
        Run(
            run_id="run-1",
            started_at=datetime(2026, 11, 14, tzinfo=UTC),
            status=RunStatus.RUNNING,
            provider="mock",
            environment="test",
        )
    )
    for tc_id in ("TC-1", "TC-2", "TC-3"):
        repository.add_test_case("run-1", make_case(tc_id))
    set_run_id("run-1")
    yield repository
    set_run_id("")


@pytest.mark.blackbox
def test_review_mode_scripts_only_approved_cases(repo: InMemoryRepository) -> None:
    set_review_status(repo, "run-1", "TC-1", ReviewStatus.APPROVED)
    set_review_status(repo, "run-1", "TC-2", ReviewStatus.REJECTED)
    ids = [c.tc_id for c in cases_for_scripting(repo, "run-1", review_mode=True)]
    assert ids == ["TC-1"]


@pytest.mark.blackbox
def test_pending_and_rejected_cases_are_never_scripted_in_review_mode(
    repo: InMemoryRepository,
) -> None:
    scripted = cases_for_scripting(repo, "run-1", review_mode=True)
    assert scripted == []
    set_review_status(repo, "run-1", "TC-3", ReviewStatus.REJECTED)
    assert cases_for_scripting(repo, "run-1", review_mode=True) == []


@pytest.mark.blackbox
def test_without_review_mode_rejected_cases_are_still_excluded(repo: InMemoryRepository) -> None:
    set_review_status(repo, "run-1", "TC-2", ReviewStatus.REJECTED)
    ids = [c.tc_id for c in cases_for_scripting(repo, "run-1", review_mode=False)]
    assert ids == ["TC-1", "TC-3"]


@pytest.mark.blackbox
def test_status_change_is_stored_and_logged(
    repo: InMemoryRepository, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        set_review_status(repo, "run-1", "TC-1", ReviewStatus.APPROVED)
    stored = {c.tc_id: c.review_status for c in repo.list_test_cases("run-1")}
    assert stored["TC-1"] is ReviewStatus.APPROVED
    assert "TC-1" in caplog.text and "Pending" in caplog.text and "Approved" in caplog.text


@pytest.mark.whitebox
def test_unknown_case_is_rejected(repo: InMemoryRepository) -> None:
    with pytest.raises(PersistenceError):
        set_review_status(repo, "run-1", "TC-404", ReviewStatus.APPROVED)


@pytest.mark.whitebox
def test_status_filter_on_repository(repo: InMemoryRepository) -> None:
    set_review_status(repo, "run-1", "TC-1", ReviewStatus.APPROVED)
    approved = repo.list_test_cases("run-1", ReviewStatus.APPROVED)
    assert [c.tc_id for c in approved] == ["TC-1"]
