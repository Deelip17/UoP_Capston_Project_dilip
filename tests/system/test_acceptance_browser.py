"""Acceptance checks AT-FR-12 and AT-FR-17 to AT-FR-19: scripts and execution in a real browser.

These need Chromium, so they carry the ``system`` marker as well as ``acceptance`` and are
excluded from the default run (``pytest -m "acceptance and system"``). They reuse one full
``aitaf run`` on the demo shop (fixture ``run_a`` of ``tests/system/conftest.py``), run by
the author as the customer (ADR-047). The first docstring line is ``AT-FR-nn: <criterion>``;
a ``PARTLY:`` line names what the check does not demonstrate.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pipeline_runner import Pipeline

pytestmark = [pytest.mark.acceptance, pytest.mark.system, pytest.mark.blackbox]

SUMMARY = re.compile(r"summary: (\d+) passed, (\d+) failed, (\d+) errors, (\d+) skipped")


def execution_folder(pipeline: Pipeline) -> Path:
    return pipeline.out / "runs" / pipeline.exec_run


def test_at_fr12_generated_playwright_scripts_pass_a_syntax_check_and_execute_on_the_shop(
    run_a: Pipeline,
) -> None:
    """AT-FR-12: a generated script passes a syntax check and executes on the sample application.

    PARTLY: every script compiles and every script executes, but only the share that passed
    or failed on an assertion ran as designed; the rest failed on a missing locator (objective
    O2, target 80%, not met: defect log L-006).
    """
    assert run_a.process.returncode == 0, run_a.process.stdout[-800:]
    scripts = run_a.out / "scripts"
    files = sorted(scripts.rglob("*.py"))
    tests = sorted((scripts / "tests").glob("test_*.py"))
    assert len(tests) == 54
    for path in files:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    repo = run_a.repo()
    try:
        results = repo.list_results(run_a.exec_run)
    finally:
        repo.close()
    assert len(results) == len(tests)
    assert {r.status for r in results} <= {"passed", "failed"}
    assert sum(1 for r in results if r.status == "passed") >= 1


def test_at_fr17_the_playwright_suite_runs_and_returns_results(run_a: Pipeline) -> None:
    """AT-FR-17: the suite runs on the driver against the sample application and returns results.

    PARTLY: only Playwright ran in a real browser; the Selenium path was exercised with a fake
    driver only, so "the same suite on both drivers" is not demonstrated (limitation L-001).
    """
    repo = run_a.repo()
    try:
        run = repo.get_run(run_a.exec_run)
        results = repo.list_results(run_a.exec_run)
    finally:
        repo.close()
    assert run is not None and run.environment.startswith("playwright")
    assert len(results) == 54
    assert all(r.status in ("passed", "failed", "error", "skipped") for r in results)
    assert all(r.duration_ms >= 0 and r.attempts >= 1 for r in results)
    assert any(r.status == "passed" for r in results)


def test_at_fr18_every_failure_has_a_screenshot_linked_to_its_result(run_a: Pipeline) -> None:
    """AT-FR-18: a screenshot file exists for each failure and is linked to its result record."""
    repo = run_a.repo()
    try:
        failures = [r for r in repo.list_results(run_a.exec_run) if r.status in ("failed", "error")]
    finally:
        repo.close()
    assert failures
    folder = execution_folder(run_a)
    report = (folder / "report.html").read_text(encoding="utf-8")
    for failure in failures:
        assert failure.screenshot, failure.tc_id
        shot = folder / failure.screenshot
        assert shot.is_file() and shot.read_bytes().startswith(b"\x89PNG"), failure.tc_id
        assert f"evidence/{failure.screenshot}" in report


def test_at_fr19_the_stored_run_matches_the_console_summary_after_the_process_exits(
    run_a: Pipeline,
) -> None:
    """AT-FR-19: after the process exits the stored run matches the console output."""
    found = SUMMARY.search(run_a.process.stdout)
    assert found, run_a.process.stdout[-800:]
    passed, failed, errors, skipped = (int(g) for g in found.groups())
    repo = run_a.repo()
    try:
        run = repo.get_run(run_a.exec_run)
        results = repo.list_results(run_a.exec_run)
    finally:
        repo.close()
    assert run is not None and run.environment and run.finished_at is not None
    counts = {s: sum(1 for r in results if r.status == s) for s in ("passed", "failed", "error")}
    assert (counts["passed"], counts["failed"], counts["error"]) == (passed, failed, errors)
    assert len(results) == passed + failed + errors + skipped
    assert all(r.duration_ms >= 0 for r in results)
    assert all(r.log for r in results if r.status in ("failed", "error"))
