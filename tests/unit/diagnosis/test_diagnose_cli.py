"""``aitaf diagnose``: analyse the failures of a stored run (FR-27 to FR-29).

Runs the real chain on a fake-browser project: ``aitaf execute`` stores the results,
``aitaf diagnose`` classifies them. The model is the mock provider.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fake_browser_project import DEFECT_TEST, ID_MUTATED_DOM, project

from aitaf.cli import main

ODD_TEST = "def test_odd(page):\n    raise RuntimeError('unexpected state')\n"
GHOST_TEST = (
    "def test_ghost(page):\n"
    "    raise LookupError('no locator strategy matched for ghost on page login')\n"
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_PROVIDER", "LLM_CALL_CAP", "OPENAI_API_KEY", "LLM_MODEL", "LLM_CACHE_DIR"):
        monkeypatch.delenv(name, raising=False)


def run_execute(tmp_path: Path, tests: dict[str, str]) -> None:
    scripts = project(tmp_path, tests, ID_MUTATED_DOM)
    main(
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
        ]
    )


def execute_failing(tmp_path: Path) -> None:
    run_execute(
        tmp_path, {"test_defect": DEFECT_TEST, "test_ghost": GHOST_TEST, "test_odd": ODD_TEST}
    )


def diagnose(tmp_path: Path, *extra: str) -> int:
    return main(
        [
            "diagnose",
            "--db",
            str(tmp_path / "x.db"),
            "--evidence",
            str(tmp_path / "evidence"),
            *extra,
        ]
    )


@pytest.mark.blackbox
def test_each_failure_is_listed_with_category_confidence_cluster_cause_and_next_step(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    execute_failing(tmp_path)
    capsys.readouterr()
    assert diagnose(tmp_path) == 0
    out = capsys.readouterr().out
    expected = (
        ("TEST-DEFECT", "assertion_defect"),
        ("TEST-GHOST", "locator"),
        ("TEST-ODD", "unknown"),
    )
    for tc, category in expected:
        line = next(line for line in out.splitlines() if line.startswith(tc))
        assert category in line and "conf=" in line and "CL-" in line
    assert "cause:" in out and "next:" in out and "evidence:" in out
    assert "summary: 3 failures analysed in 3 cluster(s)" in out
    assert "1 model call(s)" in out


@pytest.mark.blackbox
def test_the_analyses_are_stored_in_the_database(tmp_path: Path) -> None:
    execute_failing(tmp_path)
    diagnose(tmp_path)
    with sqlite3.connect(tmp_path / "x.db") as conn:
        count = conn.execute("SELECT COUNT(*) FROM failure_analyses").fetchone()[0]
    assert count == 3


@pytest.mark.blackbox
def test_no_llm_leaves_the_ambiguous_failure_as_a_labelled_fallback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    execute_failing(tmp_path)
    capsys.readouterr()
    assert diagnose(tmp_path, "--no-llm") == 0
    out = capsys.readouterr().out
    assert "0 model call(s)" in out
    odd = next(line for line in out.splitlines() if line.startswith("TEST-ODD"))
    assert "[fallback]" in odd


@pytest.mark.whitebox
def test_a_run_without_results_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert diagnose(tmp_path) == 1
    assert "aitaf execute" in capsys.readouterr().err


@pytest.mark.whitebox
def test_an_unknown_run_id_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    execute_failing(tmp_path)
    capsys.readouterr()
    assert diagnose(tmp_path, "--run", "no-such-run") == 1
    assert "no-such-run" in capsys.readouterr().err


@pytest.mark.whitebox
def test_a_run_where_everything_passed_has_nothing_to_analyse(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_execute(tmp_path, {"test_fine": "def test_fine(page):\n    pass\n"})
    capsys.readouterr()
    assert diagnose(tmp_path) == 0
    assert "no failed tests to analyse" in capsys.readouterr().out
