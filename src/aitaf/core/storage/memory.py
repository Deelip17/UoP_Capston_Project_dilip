"""In-memory fake repository for component tests (NFR-24)."""

from __future__ import annotations

from datetime import datetime

from aitaf.core.errors import PersistenceError
from aitaf.core.models import (
    AnalyzedRequirement,
    LlmAudit,
    Locator,
    ReviewStatus,
    Run,
    RunStatus,
    Script,
    TestCase,
    TestData,
    TestResult,
    TestScenario,
)


class InMemoryRepository:
    """Dictionary-backed repository with the same behaviour as the SQLite one."""

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._results: list[TestResult] = []
        self._audits: list[LlmAudit] = []
        self._requirements: dict[tuple[str, str], AnalyzedRequirement] = {}
        self._scenarios: dict[tuple[str, str], TestScenario] = {}
        self._cases: dict[tuple[str, str], TestCase] = {}
        self._data: dict[tuple[str, str], TestData] = {}
        self._scripts: dict[tuple[str, str], Script] = {}
        self._locators: dict[tuple[str, str], Locator] = {}

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

    def add_requirement(self, run_id: str, requirement: AnalyzedRequirement) -> None:
        self._require_run(run_id)
        self._requirements[(run_id, requirement.req_id)] = requirement

    def list_requirements(self, run_id: str) -> list[AnalyzedRequirement]:
        return [r for (rid, _), r in self._requirements.items() if rid == run_id]

    def latest_run_with_requirements(self) -> str | None:
        return next(reversed(self._requirements))[0] if self._requirements else None

    def add_scenario(self, run_id: str, scenario: TestScenario) -> None:
        self._require_run(run_id)
        self._scenarios[(run_id, scenario.scenario_id)] = scenario

    def list_scenarios(self, run_id: str) -> list[TestScenario]:
        return [s for (rid, _), s in self._scenarios.items() if rid == run_id]

    def add_test_case(self, run_id: str, case: TestCase) -> None:
        self._require_run(run_id)
        self._cases[(run_id, case.tc_id)] = case

    def list_test_cases(self, run_id: str, status: ReviewStatus | None = None) -> list[TestCase]:
        return [
            c
            for (rid, _), c in self._cases.items()
            if rid == run_id and (status is None or c.review_status is status)
        ]

    def set_review_status(self, run_id: str, tc_id: str, status: ReviewStatus) -> None:
        case = self._cases.get((run_id, tc_id))
        if case is None:
            raise PersistenceError(f"unknown test case: {tc_id!r}")
        self._cases[(run_id, tc_id)] = case.model_copy(update={"review_status": status})

    def add_test_data(self, run_id: str, data: TestData) -> None:
        self._require_run(run_id)
        self._data[(run_id, data.tc_id)] = data

    def list_test_data(self, run_id: str) -> list[TestData]:
        return [d for (rid, _), d in self._data.items() if rid == run_id]

    def add_script(self, run_id: str, script: Script) -> None:
        self._require_run(run_id)
        self._scripts[(run_id, script.script_id)] = script

    def list_scripts(self, run_id: str) -> list[Script]:
        return [s for (rid, _), s in self._scripts.items() if rid == run_id]

    def add_locator(self, run_id: str, locator: Locator) -> None:
        self._require_run(run_id)
        self._locators[(run_id, locator.loc_id)] = locator

    def list_locators(self, run_id: str) -> list[Locator]:
        return [loc for (rid, _), loc in self._locators.items() if rid == run_id]

    def close(self) -> None:
        return None
