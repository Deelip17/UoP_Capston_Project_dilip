"""PyTest plugin loaded by the Execution Engine (``-p aitaf.execution.plugin``).

It records one JSON line per test (outcome, duration, message, attempt) and, for a
failing test, a screenshot and a DOM snapshot taken from the ``page`` (Playwright)
or ``driver`` (Selenium) fixture. Evidence is best effort: a problem taking it is
never allowed to hide the real test outcome. File names are built from the test
id with every unsafe character replaced, so evidence cannot leave its directory
(FR-18, FR-19, FR-20, NFR-11). The plugin imports only the standard library and
pytest so it loads fast in every worker process.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

MAX_MESSAGE = 4000
MAX_ERROR_TEXT = 500
_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("aitaf", "AITAF Execution Engine")
    group.addoption("--aitaf-results", default="", help="directory for result lines (JSONL)")
    group.addoption("--aitaf-evidence", default="", help="directory for screenshots and DOM files")
    group.addoption("--aitaf-attempt", type=int, default=1, help="attempt number of this run")
    group.addoption("--aitaf-headed", action="store_true", default=False, help="show the browser")
    group.addoption("--aitaf-timeout-ms", type=int, default=10_000, help="default action timeout")
    group.addoption("--aitaf-allowed-hosts", default="", help="comma-separated browser allow-list")
    group.addoption(
        "--aitaf-checkpoints", action="store_true", default=False, help="screenshot passing tests"
    )


def _safe_name(nodeid: str, attempt: int) -> str:
    return f"{_UNSAFE.sub('_', nodeid).strip('_')[-120:]}.a{attempt}"


def _write_evidence(item: pytest.Item, evidence: Path, attempt: int) -> tuple[str, str]:
    """Take a screenshot and a DOM snapshot if the test has a browser fixture."""
    funcargs: dict[str, Any] = getattr(item, "funcargs", {})
    browser = funcargs.get("page") or funcargs.get("driver")
    if browser is None:
        return "", ""
    base = _safe_name(item.nodeid, attempt)
    evidence.mkdir(parents=True, exist_ok=True)
    shot, dom = "", ""
    try:
        target = evidence / f"{base}.png"
        if hasattr(browser, "screenshot"):
            browser.screenshot(path=str(target))
        else:
            browser.save_screenshot(str(target))
        shot = target.name
    except Exception:  # best effort: never hide the test outcome
        shot = ""
    try:
        html = browser.content() if hasattr(browser, "content") else browser.page_source
        target = evidence / f"{base}.html"
        target.write_text(str(html), encoding="utf-8")
        dom = target.name
    except Exception:
        dom = ""
    return shot, dom


def _record(config: pytest.Config, line: dict[str, object]) -> None:
    directory = str(config.getoption("--aitaf-results"))
    if not directory:
        return
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    with (path / f"{os.getpid()}.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line) + "\n")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, Any, None]:
    outcome = yield
    report = outcome.get_result()
    config = item.config
    if not str(config.getoption("--aitaf-results")):
        return
    failed = report.outcome == "failed"
    if (
        report.when == "call"
        or (report.when == "setup" and report.outcome != "passed")
        or (report.when == "teardown" and failed)
    ):
        if report.when == "call":
            status = {"passed": "passed", "failed": "failed", "skipped": "skipped"}[report.outcome]
        elif report.outcome == "skipped":
            status = "skipped"
        else:
            status = "error"
        attempt = int(config.getoption("--aitaf-attempt"))
        evidence_dir = str(config.getoption("--aitaf-evidence"))
        shot, dom = "", ""
        wants_evidence = status in ("failed", "error") or (
            status == "passed" and bool(config.getoption("--aitaf-checkpoints"))
        )
        if evidence_dir and wants_evidence:
            shot, dom = _write_evidence(item, Path(evidence_dir), attempt)
        message = str(report.longrepr) if report.longrepr else ""
        error_type, error_text = "", ""
        if call.excinfo is not None and status in ("failed", "error"):
            error_type = call.excinfo.typename
            error_text = str(call.excinfo.value)[:MAX_ERROR_TEXT]
        _record(
            config,
            {
                "nodeid": item.nodeid,
                "outcome": status,
                "when": report.when,
                "duration_s": float(report.duration),
                "message": message[:MAX_MESSAGE],
                "error_type": error_type,
                "error_text": error_text,
                "screenshot": shot,
                "dom": dom,
                "attempt": attempt,
            },
        )
