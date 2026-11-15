"""Human review gate for generated test cases (FR-10, NFR-31).

New cases are Pending. In review mode only Approved cases go on to script
generation; Rejected cases never do. Every status change is logged.
"""

from __future__ import annotations

from aitaf.core.errors import PersistenceError
from aitaf.core.logging import get_logger
from aitaf.core.models import ReviewStatus, TestCase
from aitaf.core.storage import Repository

_log = get_logger(__name__)


def set_review_status(repo: Repository, run_id: str, tc_id: str, status: ReviewStatus) -> None:
    """Change a case's review status and log the transition."""
    current = next((c for c in repo.list_test_cases(run_id) if c.tc_id == tc_id), None)
    if current is None:
        raise PersistenceError(f"unknown test case: {tc_id!r}")
    repo.set_review_status(run_id, tc_id, status)
    _log.info(
        "review status of %s changed %s -> %s", tc_id, current.review_status.value, status.value
    )


def cases_for_scripting(repo: Repository, run_id: str, review_mode: bool) -> list[TestCase]:
    """Cases allowed to move on: Approved only in review mode, else anything not Rejected."""
    if review_mode:
        return repo.list_test_cases(run_id, ReviewStatus.APPROVED)
    return [c for c in repo.list_test_cases(run_id) if c.review_status is not ReviewStatus.REJECTED]
