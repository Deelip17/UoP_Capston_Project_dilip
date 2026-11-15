"""The ``aitaf execute`` command (FR-17, FR-19, FR-21, FR-35).

Runs a fake-browser project through the real command line. Exit codes: 0 when every
test passed, 1 when a test failed or the run was refused, 2 for usage errors.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from aitaf.cli import main

CONFTEST = """
import pytest


def pytest_addoption(parser):
    parser.addoption("--base-url", default="http://127.0.0.1:1")


class FakePage:
    def screenshot(self, path):
        open(path, "wb").write(b"\\x89PNG fake")

    def content(self):
        return "<html>fake</html>"


@pytest.fixture
def page():
    yield FakePage()
"""


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_PROVIDER", "LLM_CALL_CAP", "OPENAI_API_KEY", "LLM_MODEL", "LLM_CACHE_DIR"):
        monkeypatch.delenv(name, raising=False)


def make_scripts(root: Path, *, failing: bool) -> Path:
    scripts = root / "scripts"
    (scripts / "tests").mkdir(parents=True)
    (scripts / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    (scripts / "tests" / "test_tc_1.py").write_text(
        "def test_tc_1(page):\n    assert True\n", encoding="utf-8"
    )
    if failing:
        (scripts / "tests" / "test_tc_2.py").write_text(
            "def test_tc_2(page):\n    assert False, 'broken'\n", encoding="utf-8"
        )
    (scripts / "manifest.json").write_text(
        json.dumps(
            [{"tc_id": "TC-1", "path": "tests/test_tc_1.py"}]
            + ([{"tc_id": "TC-2", "path": "tests/test_tc_2.py"}] if failing else [])
        ),
        encoding="utf-8",
    )
    return scripts


def execute(tmp_path: Path, scripts: Path, *extra: str) -> int:
    return main(
        [
            "execute",
            "--scripts",
            str(scripts),
            "--base-url",
            "http://127.0.0.1:8765",
            "--db",
            str(tmp_path / "x.db"),
            "--evidence",
            str(tmp_path / "evidence"),
            *extra,
        ]
    )


def rows(tmp_path: Path) -> list[tuple[str, str, int]]:
    with sqlite3.connect(tmp_path / "x.db") as conn:
        return conn.execute(
            "SELECT tc_id, status, attempts FROM test_results ORDER BY tc_id"
        ).fetchall()


@pytest.mark.blackbox
def test_execute_prints_results_and_stores_them(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = execute(tmp_path, make_scripts(tmp_path, failing=False))
    out = capsys.readouterr().out
    assert code == 0
    assert "PASSED" in out and "TC-1" in out
    assert "summary: 1 passed, 0 failed, 0 errors, 0 skipped" in out
    assert rows(tmp_path) == [("TC-1", "passed", 1)]


@pytest.mark.blackbox
def test_a_failing_test_gives_exit_code_one_and_a_screenshot(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = execute(tmp_path, make_scripts(tmp_path, failing=True), "--retries", "1")
    out = capsys.readouterr().out
    assert code == 1
    assert "FAILED" in out and "TC-2" in out and "attempts=2" in out
    assert rows(tmp_path) == [("TC-1", "passed", 1), ("TC-2", "failed", 2)]
    assert list((tmp_path / "evidence").rglob("*.png"))


@pytest.mark.blackbox
def test_a_url_outside_the_allow_list_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scripts = make_scripts(tmp_path, failing=False)
    code = main(
        [
            "execute",
            "--scripts",
            str(scripts),
            "--base-url",
            "http://www.example.org",
            "--db",
            str(tmp_path / "x.db"),
            "--evidence",
            str(tmp_path / "evidence"),
        ]
    )
    assert code == 1
    assert "allow-list" in capsys.readouterr().err
    assert not (tmp_path / "evidence").exists()


@pytest.mark.whitebox
def test_an_extra_allowed_host_makes_the_run_possible(tmp_path: Path) -> None:
    scripts = make_scripts(tmp_path, failing=False)
    code = main(
        [
            "execute",
            "--scripts",
            str(scripts),
            "--base-url",
            "http://shop.example.test",
            "--allow-host",
            "shop.example.test",
            "--db",
            str(tmp_path / "x.db"),
            "--evidence",
            str(tmp_path / "evidence"),
        ]
    )
    assert code == 0


@pytest.mark.whitebox
def test_missing_arguments_are_a_usage_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as info:
        main(["execute", "--db", str(tmp_path / "x.db")])
    assert info.value.code == 2


def run_statuses(tmp_path: Path) -> list[str]:
    with sqlite3.connect(tmp_path / "x.db") as conn:
        return [row[0] for row in conn.execute("SELECT status FROM runs")]


@pytest.mark.whitebox
def test_a_run_with_failing_tests_is_still_a_completed_run(tmp_path: Path) -> None:
    execute(tmp_path, make_scripts(tmp_path, failing=True))
    assert run_statuses(tmp_path) == ["completed"]


@pytest.mark.whitebox
def test_a_refused_run_is_recorded_as_failed(tmp_path: Path) -> None:
    scripts = make_scripts(tmp_path, failing=False)
    main(
        [
            "execute",
            "--scripts",
            str(scripts),
            "--base-url",
            "http://www.example.org",
            "--db",
            str(tmp_path / "x.db"),
        ]
    )
    assert run_statuses(tmp_path) == ["failed"]
