"""Repository interface for the SQLite Persistence layer (NFR-24).

Components depend on this protocol, never on the database driver, so SQLite can
be replaced and tests can use :class:`~aitaf.core.storage.memory.InMemoryRepository`.
Requirements: FR-19 (store runs and results), FR-37 (audit records), NFR-07
(interrupted runs are reported as incomplete).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from aitaf.core.models import AnalyzedRequirement, LlmAudit, Run, RunStatus, TestResult


class Repository(Protocol):
    """Storage operations shared by every module."""

    def create_run(self, run: Run) -> None:
        """Store a new run. Raises PersistenceError if the run ID exists."""

    def finish_run(self, run_id: str, status: RunStatus, finished_at: datetime) -> None:
        """Set the final status and end time. Raises PersistenceError if unknown."""

    def get_run(self, run_id: str) -> Run | None:
        """Return the run, or None if it does not exist."""

    def recover_interrupted_runs(self) -> int:
        """Mark every run still RUNNING as INCOMPLETE; return how many (NFR-07)."""

    def add_result(self, result: TestResult) -> None:
        """Store a test result. Raises PersistenceError if the run is unknown."""

    def list_results(self, run_id: str) -> list[TestResult]:
        """Return the run's results in insertion order."""

    def add_audit(self, audit: LlmAudit) -> None:
        """Store an LLM audit record. Raises PersistenceError if the run is unknown."""

    def list_audits(self, run_id: str) -> list[LlmAudit]:
        """Return the run's audit records in insertion order."""

    def add_requirement(self, run_id: str, requirement: AnalyzedRequirement) -> None:
        """Store (or replace) an analysed requirement for the run. Unknown run raises."""

    def list_requirements(self, run_id: str) -> list[AnalyzedRequirement]:
        """Return the run's analysed requirements in insertion order."""

    def close(self) -> None:
        """Release resources."""
