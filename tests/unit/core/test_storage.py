"""Repository contract tests, run against the in-memory fake and real SQLite.

Requirements: FR-19 (store runs and results), NFR-07 (durable run state),
NFR-24 (storage behind a repository interface), FR-34 (traceability by run ID).
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aitaf.core.errors import PersistenceError
from aitaf.core.models import (
    AnalyzedRequirement,
    LlmAudit,
    Locator,
    LocatorStrategy,
    ReviewStatus,
    RiskLevel,
    Run,
    RunStatus,
    Script,
    TestCase,
    TestData,
    TestResult,
    TestScenario,
)
from aitaf.core.storage import InMemoryRepository, Repository, SqliteRepository
from aitaf.core.storage.sqlite import LATEST_SCHEMA_VERSION

NOW = datetime(2026, 11, 14, 10, 0, 0, tzinfo=UTC)


def make_run(run_id: str = "run-1", status: RunStatus = RunStatus.RUNNING) -> Run:
    return Run(
        run_id=run_id,
        started_at=NOW,
        status=status,
        provider="mock",
        environment="py3.12-test",
    )


def make_result(result_id: str = "res-1", run_id: str = "run-1") -> TestResult:
    return TestResult(
        result_id=result_id,
        run_id=run_id,
        tc_id="TC-001",
        status="passed",
        duration_ms=42,
        log="ok",
    )


def make_audit(call_id: str = "call-1", run_id: str = "run-1") -> LlmAudit:
    return LlmAudit(
        call_id=call_id,
        run_id=run_id,
        component="requirement_analyzer",
        provider="mock",
        model="mock-1",
        prompt_version="ra-v1",
        tokens_in=10,
        tokens_out=5,
        input_hash="a" * 64,
        status="ok",
        mock=True,
        created_at=NOW,
    )


def make_requirement(req_id: str = "REQ-1") -> AnalyzedRequirement:
    return AnalyzedRequirement(
        req_id=req_id,
        source_ref="f.md#1",
        content_hash="h",
        actors=["user"],
        actions=["log in"],
        outcomes=["logged in"],
        risk=RiskLevel.HIGH,
        risk_rationale="why",
        ambiguity_flags=["vague"],
        prompt_version="ra-v1",
    )


@pytest.fixture(params=["memory", "sqlite"])
def repo(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Repository]:
    instance: Repository
    if request.param == "memory":
        instance = InMemoryRepository()
    else:
        instance = SqliteRepository(tmp_path / "aitaf.db")
    yield instance
    instance.close()


@pytest.mark.blackbox
def test_run_round_trip(repo: Repository) -> None:
    run = make_run()
    repo.create_run(run)
    assert repo.get_run("run-1") == run


@pytest.mark.blackbox
def test_unknown_run_returns_none(repo: Repository) -> None:
    assert repo.get_run("missing") is None


@pytest.mark.blackbox
def test_finish_run_sets_status_and_time(repo: Repository) -> None:
    repo.create_run(make_run())
    finished = datetime(2026, 11, 14, 10, 5, 0, tzinfo=UTC)
    repo.finish_run("run-1", RunStatus.COMPLETED, finished)
    stored = repo.get_run("run-1")
    assert stored is not None
    assert stored.status is RunStatus.COMPLETED
    assert stored.finished_at == finished


@pytest.mark.blackbox
def test_finish_unknown_run_raises(repo: Repository) -> None:
    with pytest.raises(PersistenceError):
        repo.finish_run("missing", RunStatus.COMPLETED, NOW)


@pytest.mark.blackbox
def test_duplicate_run_id_rejected(repo: Repository) -> None:
    repo.create_run(make_run())
    with pytest.raises(PersistenceError):
        repo.create_run(make_run())


@pytest.mark.blackbox
def test_results_are_stored_per_run(repo: Repository) -> None:
    repo.create_run(make_run("run-1"))
    repo.create_run(make_run("run-2"))
    repo.add_result(make_result("res-1", "run-1"))
    repo.add_result(make_result("res-2", "run-2"))
    assert [r.result_id for r in repo.list_results("run-1")] == ["res-1"]


@pytest.mark.blackbox
def test_result_for_unknown_run_rejected(repo: Repository) -> None:
    with pytest.raises(PersistenceError):
        repo.add_result(make_result(run_id="missing"))


@pytest.mark.blackbox
def test_audits_are_stored_per_run(repo: Repository) -> None:
    repo.create_run(make_run())
    repo.add_audit(make_audit("call-1"))
    repo.add_audit(make_audit("call-2"))
    assert [a.call_id for a in repo.list_audits("run-1")] == ["call-1", "call-2"]


@pytest.mark.blackbox
def test_audit_for_unknown_run_rejected(repo: Repository) -> None:
    with pytest.raises(PersistenceError):
        repo.add_audit(make_audit(run_id="missing"))


@pytest.mark.blackbox
def test_recover_marks_running_runs_incomplete(repo: Repository) -> None:
    repo.create_run(make_run("run-1", RunStatus.RUNNING))
    repo.create_run(make_run("run-2", RunStatus.COMPLETED))
    assert repo.recover_interrupted_runs() == 1
    first = repo.get_run("run-1")
    second = repo.get_run("run-2")
    assert first is not None and first.status is RunStatus.INCOMPLETE
    assert second is not None and second.status is RunStatus.COMPLETED


@pytest.mark.whitebox
def test_new_database_is_at_latest_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "aitaf.db"
    SqliteRepository(path).close()
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION


@pytest.mark.whitebox
def test_reopening_database_keeps_data_and_version(tmp_path: Path) -> None:
    path = tmp_path / "aitaf.db"
    first = SqliteRepository(path)
    first.create_run(make_run())
    first.close()
    second = SqliteRepository(path)
    assert second.get_run("run-1") is not None
    second.close()
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION


@pytest.mark.whitebox
def test_database_from_newer_schema_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "aitaf.db"
    with sqlite3.connect(path) as conn:
        conn.execute(f"PRAGMA user_version = {LATEST_SCHEMA_VERSION + 1}")
    with pytest.raises(PersistenceError):
        SqliteRepository(path)


@pytest.mark.whitebox
def test_foreign_keys_are_enforced_by_sqlite(tmp_path: Path) -> None:
    path = tmp_path / "aitaf.db"
    SqliteRepository(path).close()
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO test_results (result_id, run_id, tc_id, status, duration_ms, log)"
                " VALUES ('r', 'nope', 'tc', 'passed', 1, '')"
            )


@pytest.mark.whitebox
def test_audit_table_has_no_prompt_or_secret_columns(tmp_path: Path) -> None:
    path = tmp_path / "aitaf.db"
    SqliteRepository(path).close()
    with sqlite3.connect(path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(llm_audit)")}
    assert {"input_hash", "tokens_in", "tokens_out", "prompt_version"} <= columns
    assert not {c for c in columns if "prompt" in c and c != "prompt_version"}
    assert not {c for c in columns if "key" in c or "secret" in c or "text" in c}


@pytest.mark.blackbox
def test_killed_process_leaves_valid_database_and_incomplete_run(tmp_path: Path) -> None:
    path = tmp_path / "aitaf.db"
    src = Path(__file__).resolve().parents[3] / "src"
    script = textwrap.dedent(
        f"""
        import os, sys
        sys.path.insert(0, {str(src)!r})
        from datetime import UTC, datetime
        from aitaf.core.models import Run, RunStatus
        from aitaf.core.storage import SqliteRepository
        repo = SqliteRepository({str(path)!r})
        repo.create_run(Run(run_id="killed", started_at=datetime.now(UTC),
                            status=RunStatus.RUNNING, provider="mock", environment="t"))
        os._exit(1)
        """
    )
    proc = subprocess.run([sys.executable, "-c", script], check=False)
    assert proc.returncode == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    repo = SqliteRepository(path)
    assert repo.recover_interrupted_runs() == 1
    run = repo.get_run("killed")
    assert run is not None and run.status is RunStatus.INCOMPLETE
    repo.close()


@pytest.mark.blackbox
def test_requirements_are_stored_per_run(repo: Repository) -> None:
    repo.create_run(make_run("run-1"))
    repo.create_run(make_run("run-2"))
    repo.add_requirement("run-1", make_requirement("REQ-1"))
    repo.add_requirement("run-2", make_requirement("REQ-2"))
    assert repo.list_requirements("run-1") == [make_requirement("REQ-1")]


@pytest.mark.blackbox
def test_adding_the_same_requirement_twice_keeps_one(repo: Repository) -> None:
    repo.create_run(make_run())
    repo.add_requirement("run-1", make_requirement())
    repo.add_requirement("run-1", make_requirement())
    assert len(repo.list_requirements("run-1")) == 1


@pytest.mark.blackbox
def test_requirement_for_unknown_run_rejected(repo: Repository) -> None:
    with pytest.raises(PersistenceError):
        repo.add_requirement("missing", make_requirement())


def make_scenario(scenario_id: str = "REQ-1-S1") -> TestScenario:
    return TestScenario(
        scenario_id=scenario_id,
        req_id="REQ-1",
        scenario_type="positive",
        description="happy path",
        model="mock-1",
        prompt_version="tg-v1",
    )


def make_case(tc_id: str = "TC-1") -> TestCase:
    return TestCase(
        tc_id=tc_id,
        req_id="REQ-1",
        scenario_id="REQ-1-S1",
        title="t",
        steps=["a"],
        expected=["b"],
        priority="M",
        model="mock-1",
        prompt_version="tg-v1",
    )


@pytest.mark.blackbox
def test_scenarios_cases_and_data_are_stored_per_run(repo: Repository) -> None:
    repo.create_run(make_run("run-1"))
    repo.create_run(make_run("run-2"))
    repo.add_scenario("run-1", make_scenario())
    repo.add_test_case("run-1", make_case("TC-1"))
    repo.add_test_case("run-2", make_case("TC-2"))
    repo.add_test_data("run-1", TestData(tc_id="TC-1", dataset={"email": "a@example.test"}))
    assert repo.list_scenarios("run-1") == [make_scenario()]
    assert [c.tc_id for c in repo.list_test_cases("run-1")] == ["TC-1"]
    assert repo.list_test_data("run-1")[0].dataset == {"email": "a@example.test"}
    assert repo.list_scenarios("run-2") == []


@pytest.mark.blackbox
def test_adding_the_same_case_twice_keeps_one(repo: Repository) -> None:
    repo.create_run(make_run())
    repo.add_test_case("run-1", make_case())
    repo.add_test_case("run-1", make_case())
    assert len(repo.list_test_cases("run-1")) == 1


@pytest.mark.blackbox
def test_review_status_update_and_filter(repo: Repository) -> None:
    repo.create_run(make_run())
    repo.add_test_case("run-1", make_case("TC-1"))
    repo.add_test_case("run-1", make_case("TC-2"))
    repo.set_review_status("run-1", "TC-2", ReviewStatus.APPROVED)
    approved = repo.list_test_cases("run-1", ReviewStatus.APPROVED)
    assert [c.tc_id for c in approved] == ["TC-2"]
    pending = repo.list_test_cases("run-1", ReviewStatus.PENDING)
    assert [c.tc_id for c in pending] == ["TC-1"]


@pytest.mark.blackbox
def test_review_status_update_for_unknown_case_raises(repo: Repository) -> None:
    repo.create_run(make_run())
    with pytest.raises(PersistenceError):
        repo.set_review_status("run-1", "TC-404", ReviewStatus.APPROVED)


@pytest.mark.blackbox
def test_generated_records_for_unknown_run_rejected(repo: Repository) -> None:
    with pytest.raises(PersistenceError):
        repo.add_test_case("missing", make_case())
    with pytest.raises(PersistenceError):
        repo.add_scenario("missing", make_scenario())
    with pytest.raises(PersistenceError):
        repo.add_test_data("missing", TestData(tc_id="TC-1", dataset={}))


@pytest.mark.blackbox
def test_latest_run_with_requirements(repo: Repository) -> None:
    assert repo.latest_run_with_requirements() is None
    repo.create_run(make_run("run-1"))
    repo.create_run(make_run("run-2"))
    repo.add_requirement("run-1", make_requirement())
    assert repo.latest_run_with_requirements() == "run-1"
    repo.add_requirement("run-2", make_requirement())
    assert repo.latest_run_with_requirements() == "run-2"


def make_locator(name: str = "email", value: str = "email") -> Locator:
    return Locator(
        loc_id=f"login.{name}",
        page="login",
        name=name,
        primary=LocatorStrategy(kind="id", value=value),
        fallbacks=[LocatorStrategy(kind="css", value="input")],
        model="mock-1",
        prompt_version="sg-v1",
    )


def make_script(script_id: str = "SCR-1") -> Script:
    return Script(
        script_id=script_id,
        tc_id="TC-1",
        framework="playwright",
        path="tests/test_tc_1.py",
        validation_result="passed",
        model="mock-1",
        prompt_version="sg-v1",
    )


@pytest.mark.blackbox
def test_scripts_and_locators_are_stored_per_run(repo: Repository) -> None:
    repo.create_run(make_run("run-1"))
    repo.create_run(make_run("run-2"))
    repo.add_script("run-1", make_script())
    repo.add_locator("run-1", make_locator("email"))
    repo.add_locator("run-1", make_locator("submit"))
    repo.add_locator("run-2", make_locator("other"))
    assert repo.list_scripts("run-1") == [make_script()]
    assert [loc.name for loc in repo.list_locators("run-1")] == ["email", "submit"]
    assert repo.list_scripts("run-2") == []


@pytest.mark.blackbox
def test_adding_the_same_locator_again_replaces_it(repo: Repository) -> None:
    repo.create_run(make_run())
    repo.add_locator("run-1", make_locator(value="a"))
    repo.add_locator("run-1", make_locator(value="b"))
    stored = repo.list_locators("run-1")
    assert len(stored) == 1 and stored[0].primary.value == "b"


@pytest.mark.blackbox
def test_script_or_locator_for_unknown_run_rejected(repo: Repository) -> None:
    with pytest.raises(PersistenceError):
        repo.add_script("missing", make_script())
    with pytest.raises(PersistenceError):
        repo.add_locator("missing", make_locator())
