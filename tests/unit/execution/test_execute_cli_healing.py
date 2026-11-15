"""``aitaf execute --heal`` (FR-22 to FR-26 through the command line, FR-25).

Uses the fake-DOM project from the engine tests: a page object over a rendered shop
page whose login button id was changed.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fake_browser_project import ID_MUTATED_DOM, LOGIN_TEST, SHOP_DOM, project

from aitaf.cli import main


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_PROVIDER", "LLM_CALL_CAP", "OPENAI_API_KEY", "LLM_MODEL", "LLM_CACHE_DIR"):
        monkeypatch.delenv(name, raising=False)


def execute(tmp_path: Path, *extra: str) -> int:
    scripts = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
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


@pytest.mark.blackbox
def test_heal_with_a_baseline_repairs_the_test_and_reports_the_rate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = execute(tmp_path, "--heal", "--baseline", str(SHOP_DOM))
    out = capsys.readouterr().out
    assert code == 0
    assert "PASSED" in out and "attempts=2" in out and "healed=1" in out
    assert "healing: 1 requested, 1 test(s) passed after healing, success rate 100%" in out
    with sqlite3.connect(tmp_path / "x.db") as conn:
        events = conn.execute("SELECT record FROM healing_events").fetchall()
    assert len(events) == 2 and any('"outcome":"proposed"' in e[0].replace(" ", "") for e in events)


@pytest.mark.blackbox
def test_without_heal_the_same_run_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = execute(tmp_path)
    out = capsys.readouterr().out
    assert code == 1 and "FAILED" in out and "healing:" not in out


@pytest.mark.whitebox
def test_without_a_baseline_the_heal_request_is_made_but_not_granted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = execute(tmp_path, "--heal")
    out = capsys.readouterr().out
    assert code == 1
    assert "healing: 1 requested, 0 test(s) passed after healing" in out


@pytest.mark.whitebox
def test_an_out_of_range_pass_limit_is_a_configuration_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert execute(tmp_path, "--heal", "--max-heal-passes", "99") == 2
    assert "max_heal_passes" in capsys.readouterr().err
