"""Failure analyses and the failure fields of test results (FR-27 to FR-29, FR-19, NFR-30).

Migration 8 adds ``nodeid``, ``error_type`` and ``error_text`` to ``test_results`` (the
Failure Analyzer works from stored results, so the failure's identity and exception
must be stored, not only the long log) and the table ``failure_analyses``.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from aitaf.core.errors import PersistenceError
from aitaf.core.models import FailureAnalysis, Run, RunStatus, TestResult
from aitaf.core.storage import InMemoryRepository, Repository, SqliteRepository
from aitaf.core.storage.sqlite import LATEST_SCHEMA_VERSION, MIGRATIONS

NOW = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)


def make_run(run_id: str = "run-1") -> Run:
    return Run(
        run_id=run_id, started_at=NOW, status=RunStatus.RUNNING, provider="mock", environment="t"
    )


def make_analysis(**extra: object) -> FailureAnalysis:
    base: dict[str, object] = {
        "analysis_id": "fa-1",
        "run_id": "run-1",
        "result_id": "res-1",
        "tc_id": "TC-1",
        "category": "locator",
        "root_cause": "The element named login_submit was not found on the page.",
        "remediation": "Review the proposed locator and approve it, or update the page object.",
        "evidence_refs": ["log:res-1", "screenshot:a.png"],
        "confidence": 0.9,
        "cluster_id": "CL-0123abcd",
        "source": "rules",
        "created_at": NOW,
    }
    return FailureAnalysis(**{**base, **extra})  # type: ignore[arg-type]


@pytest.fixture(params=["memory", "sqlite"])
def repo(request: pytest.FixtureRequest, tmp_path: Path) -> Repository:
    return (
        InMemoryRepository() if request.param == "memory" else SqliteRepository(tmp_path / "f.db")
    )


# ----------------------------------------------------------------------- results


@pytest.mark.blackbox
def test_failure_fields_of_a_result_default_to_empty_and_round_trip(repo: Repository) -> None:
    repo.create_run(make_run())
    plain = TestResult(result_id="r0", run_id="run-1", tc_id="TC-0", status="passed", duration_ms=1)
    assert (plain.nodeid, plain.error_type, plain.error_text) == ("", "", "")
    failed = TestResult(
        result_id="r1",
        run_id="run-1",
        tc_id="TC-1",
        status="failed",
        duration_ms=5,
        nodeid="tests/test_a.py::test_a",
        error_type="AssertionError",
        error_text="assert 1 == 2",
    )
    repo.add_result(failed)
    assert repo.list_results("run-1") == [failed]


@pytest.mark.blackbox
def test_the_latest_run_with_results_is_found(repo: Repository) -> None:
    repo.create_run(make_run("run-1"))
    repo.create_run(make_run("run-2"))
    assert repo.latest_run_with_results() is None
    repo.add_result(
        TestResult(result_id="r", run_id="run-1", tc_id="T", status="failed", duration_ms=1)
    )
    assert repo.latest_run_with_results() == "run-1"


@pytest.mark.blackbox
def test_runs_with_results_are_listed_oldest_first_once_each(repo: Repository) -> None:
    for run_id in ("run-1", "run-2", "run-3"):
        repo.create_run(make_run(run_id))
    assert repo.list_runs_with_results() == []
    for index, run_id in enumerate(("run-2", "run-2", "run-1")):
        repo.add_result(
            TestResult(
                result_id=f"r{index}", run_id=run_id, tc_id="T", status="passed", duration_ms=1
            )
        )
    assert repo.list_runs_with_results() == ["run-2", "run-1"]


# --------------------------------------------------------------------- analyses


@pytest.mark.blackbox
def test_an_analysis_round_trips_and_is_listed_in_insertion_order(repo: Repository) -> None:
    repo.create_run(make_run())
    first = make_analysis()
    second = make_analysis(analysis_id="fa-2", result_id="res-2", category="unknown")
    repo.add_failure_analysis("run-1", first)
    repo.add_failure_analysis("run-1", second)
    assert repo.list_failure_analyses("run-1") == [first, second]
    assert repo.list_failure_analyses("run-2") == []


@pytest.mark.whitebox
def test_adding_the_same_analysis_again_replaces_it(repo: Repository) -> None:
    repo.create_run(make_run())
    repo.add_failure_analysis("run-1", make_analysis())
    repo.add_failure_analysis("run-1", make_analysis(confidence=0.5))
    (only,) = repo.list_failure_analyses("run-1")
    assert only.confidence == 0.5


@pytest.mark.whitebox
def test_an_analysis_for_an_unknown_run_is_rejected(repo: Repository) -> None:
    with pytest.raises(PersistenceError):
        repo.add_failure_analysis("nope", make_analysis(run_id="nope"))


@pytest.mark.blackbox
@pytest.mark.parametrize(
    "extra",
    [
        {"category": "network"},
        {"confidence": 1.1},
        {"confidence": -0.1},
        {"cluster_id": "cluster-1"},
        {"root_cause": ""},
        {"remediation": ""},
        {"source": "llm"},  # an AI answer must name its model and prompt version (NFR-30)
    ],
)
def test_invalid_analyses_are_rejected(extra: dict[str, object]) -> None:
    with pytest.raises(PydanticValidationError):
        make_analysis(**extra)


@pytest.mark.whitebox
def test_an_ai_analysis_carries_its_model_and_prompt_version() -> None:
    analysis = make_analysis(source="llm", model="gpt-test", prompt_version="fa-v1")
    assert (analysis.model, analysis.prompt_version) == ("gpt-test", "fa-v1")


@pytest.mark.whitebox
def test_a_version_seven_database_is_upgraded_and_keeps_its_results(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:
        for statement in "".join(MIGRATIONS[:7]).split(";"):
            if statement.strip():
                conn.execute(statement)
        conn.execute("PRAGMA user_version = 7")
        conn.execute(
            "INSERT INTO runs (run_id, started_at, finished_at, status, provider, environment)"
            " VALUES ('run-1', ?, NULL, 'running', 'mock', 'test')",
            (NOW.isoformat(),),
        )
        conn.execute(
            "INSERT INTO test_results (result_id, run_id, tc_id, status, duration_ms, log)"
            " VALUES ('res-0', 'run-1', 'TC-0', 'failed', 5, 'boom')"
        )
    upgraded = SqliteRepository(path)
    try:
        (old,) = upgraded.list_results("run-1")
        assert old.error_type == "" and old.nodeid == "" and old.log == "boom"
        assert upgraded.list_failure_analyses("run-1") == []
    finally:
        upgraded.close()
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION >= 8
