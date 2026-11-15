"""In-memory fake repository for component tests (NFR-24)."""

from __future__ import annotations

from datetime import datetime

from aitaf.core.errors import PersistenceError
from aitaf.core.models import LlmAudit, Run, RunStatus, TestResult


class InMemoryRepository:
    """Dictionary-backed repository with the same behaviour as the SQLite one."""

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._results: list[TestResult] = []
        self._audits: list[LlmAudit] = []

    def _require_run(self, run_id: str) -> None:
        if run_id not in self._runs:
            raise PersistenceError(f"unknown run: {run_id!r}")

    def create_run(self, run: Run) -> None:
        if run.run_id in self._runs:
            raise PersistenceError(f"run already exists: {run.run_id!r}")
        self._runs[run.run_id] = run

    def finish_run(self, run_id: str, status: RunStatus, finished_at: datetime) -> None:
        self._require_run(run_id)
        self._runs[run_id] = self._runs[run_id].model_copy(
            update={"status": status, "finished_at": finished_at}
        )

    def get_run(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    def recover_interrupted_runs(self) -> int:
        stale = [r for r in self._runs.values() if r.status is RunStatus.RUNNING]
        for run in stale:
            self._runs[run.run_id] = run.model_copy(update={"status": RunStatus.INCOMPLETE})
        return len(stale)

    def add_result(self, result: TestResult) -> None:
        self._require_run(result.run_id)
        self._results.append(result)

    def list_results(self, run_id: str) -> list[TestResult]:
        return [r for r in self._results if r.run_id == run_id]

    def add_audit(self, audit: LlmAudit) -> None:
        self._require_run(audit.run_id)
        self._audits.append(audit)

    def list_audits(self, run_id: str) -> list[LlmAudit]:
        return [a for a in self._audits if a.run_id == run_id]

    def close(self) -> None:
        return None
