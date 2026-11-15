"""Test results carry attempts and evidence paths (FR-18, FR-19, FR-20, FR-34).

Migration 7 adds ``attempts`` (retry count per test, FR-20), ``screenshot`` and
``dom_snapshot`` (evidence links, FR-18) to ``test_results``. A database created
before the migration must keep its rows.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from aitaf.core.models import Run, RunStatus, TestResult
from aitaf.core.storage import InMemoryRepository, Repository, SqliteRepository
from aitaf.core.storage.sqlite import LATEST_SCHEMA_VERSION, MIGRATIONS

NOW = datetime(2026, 11, 15, 10, 0, 0, tzinfo=UTC)


def make_run(run_id: str = "run-1") -> Run:
    return Run(
        run_id=run_id,
        started_at=NOW,
        status=RunStatus.RUNNING,
        provider="mock",
        environment="test",
    )


def make_result(**extra: object) -> TestResult:
    base: dict[str, object] = {
        "result_id": "res-1",
        "run_id": "run-1",
        "tc_id": "TC-1",
        "status": "failed",
        "duration_ms": 120,
        "log": "assert False",
    }
    return TestResult(**{**base, **extra})  # type: ignore[arg-type]


@pytest.fixture(params=["memory", "sqlite"])
def repo(request: pytest.FixtureRequest, tmp_path: Path) -> Repository:
    return (
        InMemoryRepository() if request.param == "memory" else SqliteRepository(tmp_path / "r.db")
    )


@pytest.mark.blackbox
def test_new_fields_have_safe_defaults() -> None:
    result = make_result()
    assert result.attempts == 1
    assert result.screenshot == "" and result.dom_snapshot == ""


@pytest.mark.blackbox
def test_attempts_must_be_at_least_one() -> None:
    with pytest.raises(PydanticValidationError):
        make_result(attempts=0)


@pytest.mark.blackbox
def test_attempts_and_evidence_paths_round_trip(repo: Repository) -> None:
    repo.create_run(make_run())
    stored = make_result(attempts=3, screenshot="shots/tc1.a3.png", dom_snapshot="dom/tc1.a3.html")
    repo.add_result(stored)
    assert repo.list_results("run-1") == [stored]


@pytest.mark.whitebox
def test_a_version_six_database_is_upgraded_and_keeps_its_results(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:
        for statement in "".join(MIGRATIONS[:6]).split(";"):
            if statement.strip():
                conn.execute(statement)
        conn.execute("PRAGMA user_version = 6")
        conn.execute(
            "INSERT INTO runs (run_id, started_at, finished_at, status, provider, environment)"
            " VALUES ('run-1', ?, NULL, 'running', 'mock', 'test')",
            (NOW.isoformat(),),
        )
        conn.execute(
            "INSERT INTO test_results (result_id, run_id, tc_id, status, duration_ms, log)"
            " VALUES ('res-0', 'run-1', 'TC-0', 'passed', 5, '')"
        )
    upgraded = SqliteRepository(path)
    try:
        (old,) = upgraded.list_results("run-1")
    finally:
        upgraded.close()
    assert old.attempts == 1 and old.screenshot == "" and old.dom_snapshot == ""
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION >= 7
