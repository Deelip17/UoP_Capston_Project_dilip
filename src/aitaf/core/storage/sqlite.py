"""SQLite implementation of the repository (FR-19, NFR-07, NFR-24).

Only this module touches the ``sqlite3`` driver. The schema is versioned with
``PRAGMA user_version`` and upgraded by ordered migrations. The database uses
write-ahead logging and enforced foreign keys, and every write is committed
immediately so a killed process leaves a consistent file (NFR-07).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from aitaf.core.errors import PersistenceError
from aitaf.core.models import (
    AnalyzedRequirement,
    LlmAudit,
    ReviewStatus,
    Run,
    RunStatus,
    TestCase,
    TestData,
    TestResult,
    TestScenario,
)

MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE runs (
        run_id TEXT PRIMARY KEY,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        provider TEXT NOT NULL,
        environment TEXT NOT NULL
    );
    CREATE TABLE test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result_id TEXT NOT NULL UNIQUE,
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        tc_id TEXT NOT NULL,
        status TEXT NOT NULL,
        duration_ms INTEGER NOT NULL,
        log TEXT NOT NULL
    );
    CREATE TABLE llm_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        call_id TEXT NOT NULL UNIQUE,
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        component TEXT NOT NULL,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        prompt_version TEXT NOT NULL,
        tokens_in INTEGER NOT NULL,
        tokens_out INTEGER NOT NULL,
        input_hash TEXT NOT NULL,
        status TEXT NOT NULL,
        mock INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        req_id TEXT NOT NULL,
        record TEXT NOT NULL,
        UNIQUE (run_id, req_id)
    );
    """,
    """
    CREATE TABLE scenarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        scenario_id TEXT NOT NULL,
        record TEXT NOT NULL,
        UNIQUE (run_id, scenario_id)
    );
    CREATE TABLE test_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        tc_id TEXT NOT NULL,
        review_status TEXT NOT NULL,
        record TEXT NOT NULL,
        UNIQUE (run_id, tc_id)
    );
    CREATE TABLE test_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL REFERENCES runs(run_id),
        tc_id TEXT NOT NULL,
        record TEXT NOT NULL,
        UNIQUE (run_id, tc_id)
    );
    """,
)
LATEST_SCHEMA_VERSION = len(MIGRATIONS)


class SqliteRepository:
    """Repository backed by a SQLite file."""

    def __init__(self, path: Path | str) -> None:
        self._conn = sqlite3.connect(str(path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def _migrate(self) -> None:
        current = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
        if current > LATEST_SCHEMA_VERSION:
            self._conn.close()
            raise PersistenceError(
                f"database schema version {current} is newer than supported {LATEST_SCHEMA_VERSION}"
            )
        for version in range(current, LATEST_SCHEMA_VERSION):
            self._conn.execute("BEGIN")
            try:
                for statement in MIGRATIONS[version].split(";"):
                    if statement.strip():
                        self._conn.execute(statement)
                self._conn.execute(f"PRAGMA user_version = {version + 1}")
                self._conn.execute("COMMIT")
            except sqlite3.Error as exc:
                self._conn.execute("ROLLBACK")
                raise PersistenceError(f"migration to version {version + 1} failed: {exc}") from exc

    def _write(self, sql: str, params: tuple[object, ...]) -> int:
        try:
            return self._conn.execute(sql, params).rowcount
        except sqlite3.IntegrityError as exc:
            raise PersistenceError(f"constraint violated: {exc}") from exc
        except sqlite3.Error as exc:
            raise PersistenceError(f"write failed: {exc}") from exc

    def create_run(self, run: Run) -> None:
        self._write(
            "INSERT INTO runs (run_id, started_at, finished_at, status, provider, environment)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                run.run_id,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
                run.status.value,
                run.provider,
                run.environment,
            ),
        )

    def finish_run(self, run_id: str, status: RunStatus, finished_at: datetime) -> None:
        changed = self._write(
            "UPDATE runs SET status = ?, finished_at = ? WHERE run_id = ?",
            (status.value, finished_at.isoformat(), run_id),
        )
        if changed == 0:
            raise PersistenceError(f"unknown run: {run_id!r}")

    def get_run(self, run_id: str) -> Run | None:
        row = self._conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return Run(
            run_id=row["run_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            status=RunStatus(row["status"]),
            provider=row["provider"],
            environment=row["environment"],
        )

    def recover_interrupted_runs(self) -> int:
        return self._write(
            "UPDATE runs SET status = ? WHERE status = ?",
            (RunStatus.INCOMPLETE.value, RunStatus.RUNNING.value),
        )

    def add_result(self, result: TestResult) -> None:
        self._write(
            "INSERT INTO test_results (result_id, run_id, tc_id, status, duration_ms, log)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                result.result_id,
                result.run_id,
                result.tc_id,
                result.status,
                result.duration_ms,
                result.log,
            ),
        )

    def list_results(self, run_id: str) -> list[TestResult]:
        rows = self._conn.execute(
            "SELECT result_id, run_id, tc_id, status, duration_ms, log"
            " FROM test_results WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [TestResult(**dict(row)) for row in rows]

    def add_audit(self, audit: LlmAudit) -> None:
        self._write(
            "INSERT INTO llm_audit (call_id, run_id, component, provider, model, prompt_version,"
            " tokens_in, tokens_out, input_hash, status, mock, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                audit.call_id,
                audit.run_id,
                audit.component,
                audit.provider,
                audit.model,
                audit.prompt_version,
                audit.tokens_in,
                audit.tokens_out,
                audit.input_hash,
                audit.status,
                int(audit.mock),
                audit.created_at.isoformat(),
            ),
        )

    def list_audits(self, run_id: str) -> list[LlmAudit]:
        rows = self._conn.execute(
            "SELECT call_id, run_id, component, provider, model, prompt_version, tokens_in,"
            " tokens_out, input_hash, status, mock, created_at"
            " FROM llm_audit WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [
            LlmAudit(**{**dict(row), "mock": bool(row["mock"]), "created_at": row["created_at"]})
            for row in rows
        ]

    def add_requirement(self, run_id: str, requirement: AnalyzedRequirement) -> None:
        self._write(
            "INSERT INTO requirements (run_id, req_id, record) VALUES (?, ?, ?)"
            " ON CONFLICT (run_id, req_id) DO UPDATE SET record = excluded.record",
            (run_id, requirement.req_id, requirement.model_dump_json()),
        )

    def list_requirements(self, run_id: str) -> list[AnalyzedRequirement]:
        rows = self._conn.execute(
            "SELECT record FROM requirements WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()
        return [AnalyzedRequirement.model_validate_json(row["record"]) for row in rows]

    def latest_run_with_requirements(self) -> str | None:
        row = self._conn.execute(
            "SELECT run_id FROM requirements ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return str(row["run_id"]) if row else None

    def add_scenario(self, run_id: str, scenario: TestScenario) -> None:
        self._write(
            "INSERT INTO scenarios (run_id, scenario_id, record) VALUES (?, ?, ?)"
            " ON CONFLICT (run_id, scenario_id) DO UPDATE SET record = excluded.record",
            (run_id, scenario.scenario_id, scenario.model_dump_json()),
        )

    def list_scenarios(self, run_id: str) -> list[TestScenario]:
        rows = self._conn.execute(
            "SELECT record FROM scenarios WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()
        return [TestScenario.model_validate_json(row["record"]) for row in rows]

    def add_test_case(self, run_id: str, case: TestCase) -> None:
        self._write(
            "INSERT INTO test_cases (run_id, tc_id, review_status, record) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (run_id, tc_id) DO UPDATE SET"
            " review_status = excluded.review_status, record = excluded.record",
            (run_id, case.tc_id, case.review_status.value, case.model_dump_json()),
        )

    def list_test_cases(self, run_id: str, status: ReviewStatus | None = None) -> list[TestCase]:
        sql = "SELECT record FROM test_cases WHERE run_id = ?"
        params: tuple[object, ...] = (run_id,)
        if status is not None:
            sql += " AND review_status = ?"
            params = (run_id, status.value)
        rows = self._conn.execute(sql + " ORDER BY id", params).fetchall()
        return [TestCase.model_validate_json(row["record"]) for row in rows]

    def set_review_status(self, run_id: str, tc_id: str, status: ReviewStatus) -> None:
        row = self._conn.execute(
            "SELECT record FROM test_cases WHERE run_id = ? AND tc_id = ?", (run_id, tc_id)
        ).fetchone()
        if row is None:
            raise PersistenceError(f"unknown test case: {tc_id!r}")
        updated = TestCase.model_validate_json(row["record"]).model_copy(
            update={"review_status": status}
        )
        self._write(
            "UPDATE test_cases SET review_status = ?, record = ? WHERE run_id = ? AND tc_id = ?",
            (status.value, updated.model_dump_json(), run_id, tc_id),
        )

    def add_test_data(self, run_id: str, data: TestData) -> None:
        self._write(
            "INSERT INTO test_data (run_id, tc_id, record) VALUES (?, ?, ?)"
            " ON CONFLICT (run_id, tc_id) DO UPDATE SET record = excluded.record",
            (run_id, data.tc_id, data.model_dump_json()),
        )

    def list_test_data(self, run_id: str) -> list[TestData]:
        rows = self._conn.execute(
            "SELECT record FROM test_data WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()
        return [TestData.model_validate_json(row["record"]) for row in rows]

    def close(self) -> None:
        self._conn.close()
