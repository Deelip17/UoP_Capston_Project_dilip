"""The pytest plugin used by the Execution Engine (FR-18, FR-19, FR-20, NFR-04).

Run in-process with ``pytester`` so the hooks are measured by coverage. A fake
``page`` fixture stands in for the browser: the plugin must take a screenshot and
a DOM snapshot of a failing test, never let an evidence problem hide the test
outcome, and write one result line per test with the attempt number.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]

CONFTEST = """
import pytest


class FakePage:
    def screenshot(self, path):
        with open(path, "wb") as handle:
            handle.write(b"\\x89PNG fake")

    def content(self):
        return "<html><body>fake page</body></html>"


@pytest.fixture
def page():
    yield FakePage()
"""

TESTS = """
import pytest


def test_passes(page):
    assert True


def test_fails(page):
    assert 1 == 2, "wrong total"


@pytest.mark.skip(reason="not now")
def test_skipped(page):
    pass


@pytest.fixture
def broken():
    raise RuntimeError("fixture exploded")


def test_setup_error(page, broken):
    pass


@pytest.fixture
def bad_teardown():
    yield
    raise RuntimeError("teardown exploded")


def test_teardown_error(page, bad_teardown):
    pass
"""


def run_plugin(pytester: pytest.Pytester, tmp_path: Path, *extra: str) -> list[dict[str, object]]:
    pytester.makeconftest(CONFTEST)
    pytester.makepyfile(test_sample=TESTS)
    results = tmp_path / "results"
    evidence = tmp_path / "evidence"
    pytester.runpytest_inprocess(
        "-p",
        "aitaf.execution.plugin",
        "--aitaf-results",
        str(results),
        "--aitaf-evidence",
        str(evidence),
        "--aitaf-attempt",
        "2",
        *extra,
    )
    lines = []
    for file in sorted(results.glob("*.jsonl")):
        lines += [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines()]
    return lines


def by_name(lines: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(line["nodeid"]).split("::")[-1]: line for line in lines}


@pytest.mark.blackbox
def test_every_outcome_is_recorded_with_its_attempt_number(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    records = by_name(run_plugin(pytester, tmp_path))
    assert {name: rec["outcome"] for name, rec in records.items()} == {
        "test_passes": "passed",
        "test_fails": "failed",
        "test_skipped": "skipped",
        "test_setup_error": "error",
        "test_teardown_error": "error",
    }
    assert {rec["attempt"] for rec in records.values()} == {2}
    assert "wrong total" in str(records["test_fails"]["message"])


@pytest.mark.blackbox
def test_a_failing_test_gets_a_screenshot_and_a_dom_snapshot(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    records = by_name(run_plugin(pytester, tmp_path))
    failed = records["test_fails"]
    shot = tmp_path / "evidence" / str(failed["screenshot"])
    dom = tmp_path / "evidence" / str(failed["dom"])
    assert shot.read_bytes().startswith(b"\x89PNG")
    assert "fake page" in dom.read_text(encoding="utf-8")
    assert shot.name.endswith(".a2.png")


@pytest.mark.blackbox
def test_passing_tests_have_no_evidence_unless_checkpoints_are_on(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    without = by_name(run_plugin(pytester, tmp_path / "a"))
    assert without["test_passes"]["screenshot"] == ""
    with_checkpoints = by_name(run_plugin(pytester, tmp_path / "b", "--aitaf-checkpoints"))
    assert (
        tmp_path / "b" / "evidence" / str(with_checkpoints["test_passes"]["screenshot"])
    ).exists()


@pytest.mark.whitebox
def test_evidence_file_names_are_confined_to_the_evidence_directory(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    records = run_plugin(pytester, tmp_path)
    evidence = (tmp_path / "evidence").resolve()
    for record in records:
        for key in ("screenshot", "dom"):
            name = str(record[key])
            if name:
                assert Path(name).name == name
                assert (evidence / name).resolve().parent == evidence


@pytest.mark.whitebox
def test_a_broken_screenshot_never_hides_the_test_outcome(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    pytester.makeconftest(
        """
import pytest

class Broken:
    def screenshot(self, path):
        raise RuntimeError("browser closed")

    def content(self):
        raise RuntimeError("browser closed")

@pytest.fixture
def page():
    yield Broken()
"""
    )
    pytester.makepyfile(test_sample="def test_fails(page):\n    assert False, 'real failure'\n")
    pytester.runpytest_inprocess(
        "-p",
        "aitaf.execution.plugin",
        "--aitaf-results",
        str(tmp_path / "r"),
        "--aitaf-evidence",
        str(tmp_path / "e"),
    )
    (line,) = [
        json.loads(text)
        for file in (tmp_path / "r").glob("*.jsonl")
        for text in file.read_text(encoding="utf-8").splitlines()
    ]
    assert line["outcome"] == "failed"
    assert "real failure" in line["message"]
    assert line["screenshot"] == "" and line["dom"] == ""


@pytest.mark.whitebox
def test_selenium_style_driver_fixture_is_supported(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    pytester.makeconftest(
        """
import pytest

class Driver:
    page_source = "<html>selenium page</html>"

    def save_screenshot(self, path):
        with open(path, "wb") as handle:
            handle.write(b"\\x89PNG selenium")
        return True

@pytest.fixture
def driver():
    yield Driver()
"""
    )
    pytester.makepyfile(test_sample="def test_fails(driver):\n    assert False\n")
    pytester.runpytest_inprocess(
        "-p",
        "aitaf.execution.plugin",
        "--aitaf-results",
        str(tmp_path / "r"),
        "--aitaf-evidence",
        str(tmp_path / "e"),
    )
    (line,) = [
        json.loads(text)
        for file in (tmp_path / "r").glob("*.jsonl")
        for text in file.read_text(encoding="utf-8").splitlines()
    ]
    assert (tmp_path / "e" / line["screenshot"]).read_bytes().startswith(b"\x89PNG")
    assert "selenium page" in (tmp_path / "e" / line["dom"]).read_text(encoding="utf-8")


@pytest.mark.whitebox
def test_long_failure_messages_are_truncated(pytester: pytest.Pytester, tmp_path: Path) -> None:
    pytester.makepyfile(test_sample="def test_fails():\n    assert False, 'x' * 20000\n")
    pytester.runpytest_inprocess(
        "-p",
        "aitaf.execution.plugin",
        "--aitaf-results",
        str(tmp_path / "r"),
        "--aitaf-evidence",
        str(tmp_path / "e"),
    )
    (line,) = [
        json.loads(text)
        for file in (tmp_path / "r").glob("*.jsonl")
        for text in file.read_text(encoding="utf-8").splitlines()
    ]
    assert len(line["message"]) <= 4100


@pytest.mark.whitebox
def test_plugin_does_nothing_without_a_results_directory(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    pytester.makepyfile(test_sample="def test_ok():\n    pass\n")
    result = pytester.runpytest_inprocess("-p", "aitaf.execution.plugin")
    result.assert_outcomes(passed=1)


@pytest.mark.blackbox
def test_failures_record_the_exception_type_and_a_short_text(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    """The healer classifies a failure by exception type and message (FR-22)."""
    records = by_name(run_plugin(pytester, tmp_path))
    assert records["test_fails"]["error_type"] == "AssertionError"
    assert "wrong total" in str(records["test_fails"]["error_text"])
    assert records["test_setup_error"]["error_type"] == "RuntimeError"
    assert records["test_passes"]["error_type"] == ""
    assert records["test_passes"]["error_text"] == ""


@pytest.mark.whitebox
def test_a_locator_lookup_error_is_recorded_with_its_message(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    pytester.makepyfile(
        test_sample=(
            "def test_missing():\n"
            "    raise LookupError('no locator strategy matched for submit on page login')\n"
        )
    )
    pytester.runpytest_inprocess(
        "-p",
        "aitaf.execution.plugin",
        "--aitaf-results",
        str(tmp_path / "r"),
        "--aitaf-evidence",
        str(tmp_path / "e"),
    )
    (line,) = [
        json.loads(text)
        for file in (tmp_path / "r").glob("*.jsonl")
        for text in file.read_text(encoding="utf-8").splitlines()
    ]
    assert line["error_type"] == "LookupError"
    assert line["error_text"] == "no locator strategy matched for submit on page login"
