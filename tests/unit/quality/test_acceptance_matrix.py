"""The acceptance matrix generator: tag, result and gap handling (NFR-20, ADR-047)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.quality.acceptance_matrix import (
    Requirement,
    build_rows,
    find_tests,
    main,
    read_requirements,
    read_results,
    render,
)

TABLE = """| ID | Requirement | Rationale | Owner | Acceptance | Tier |
|---|---|---|---|---|---|
| FR-01 | The system shall do one. | why | A | One works. | M |
| FR-02 | The system shall do two. | why | A | Two works. | S |
| FR-03 | The system shall do three. | why | A | Three works. | M |
| FR-04 | The system shall do four. | why | A | Four works. | C |
"""
TESTS = '''
def test_one():
    """AT-FR-01: one works."""


def test_two():
    """AT-FR-02: two works.

    PARTLY: only the fake driver ran.
    """


def test_three_a():
    """AT-FR-03: first half of three."""


def test_three_b():
    """AT-FR-03: second half of three."""


def helper():
    """AT-FR-04 is only a helper, not a test."""


def test_no_tag():
    """Nothing to do with a requirement."""
'''
JUNIT = """<testsuites><testsuite>
<testcase classname="t" name="test_one"/>
<testcase classname="t" name="test_two"/>
<testcase classname="t" name="test_three_a"/>
<testcase classname="t" name="test_three_b"><failure message="boom"/></testcase>
</testsuite></testsuites>"""


@pytest.fixture
def files(tmp_path: Path) -> tuple[Path, Path, Path]:
    table = tmp_path / "frs.md"
    table.write_text(TABLE, encoding="utf-8")
    folder = tmp_path / "acceptance"
    folder.mkdir()
    (folder / "test_x.py").write_text(TESTS, encoding="utf-8")
    junit = tmp_path / "r.xml"
    junit.write_text(JUNIT, encoding="utf-8")
    return table, folder, junit


@pytest.mark.blackbox
def test_requirements_are_read_with_their_criterion_and_tier(files) -> None:  # type: ignore[no-untyped-def]
    table, _, _ = files
    found = read_requirements(table)
    assert [r.fr_id for r in found] == ["FR-01", "FR-02", "FR-03", "FR-04"]
    assert found[0] == Requirement("FR-01", "The system shall do one.", "One works.", "M")


@pytest.mark.blackbox
def test_only_tagged_test_functions_are_found_and_partly_lines_are_kept(files) -> None:  # type: ignore[no-untyped-def]
    _, folder, _ = files
    found = {t.function: t for t in find_tests([folder])}
    assert set(found) == {"test_one", "test_two", "test_three_a", "test_three_b"}
    assert found["test_two"].partly == "only the fake driver ran."
    assert found["test_one"].partly == ""


@pytest.mark.blackbox
def test_results_decide_met_partly_met_not_met_and_the_gaps(files) -> None:  # type: ignore[no-untyped-def]
    table, folder, junit = files
    rows = build_rows(read_requirements(table), find_tests([folder]), read_results([junit]))
    assert [r.result for r in rows] == ["Met", "Partly met", "Not met", "No test"]


@pytest.mark.whitebox
def test_a_test_without_a_result_is_reported_as_no_result(files) -> None:  # type: ignore[no-untyped-def]
    table, folder, _ = files
    rows = build_rows(read_requirements(table), find_tests([folder]), {})
    assert rows[0].result == "No result"


@pytest.mark.whitebox
def test_a_skipped_test_is_not_counted_as_met(tmp_path: Path, files) -> None:  # type: ignore[no-untyped-def]
    table, folder, _ = files
    junit = tmp_path / "s.xml"
    junit.write_text('<testsuite><testcase name="test_one"><skipped/></testcase></testsuite>')
    rows = build_rows(read_requirements(table), find_tests([folder]), read_results([junit]))
    assert rows[0].result == "Skipped"


@pytest.mark.blackbox
def test_the_rendered_matrix_has_a_summary_and_one_row_per_requirement(files) -> None:  # type: ignore[no-untyped-def]
    table, folder, junit = files
    text = render(build_rows(read_requirements(table), find_tests([folder]), read_results([junit])))
    assert "**Summary (4 requirements):** 1 met, 1 partly met, 1 not met, 1 no test." in text
    assert text.count("\n| FR-") == 4
    assert "| FR-02 |" in text and "only the fake driver ran." in text


@pytest.mark.blackbox
def test_the_command_line_writes_the_file(files, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    table, folder, junit = files
    out = tmp_path / "matrix.md"
    code = main(
        [
            "--requirements",
            str(table),
            "--tests",
            str(folder),
            "--junit",
            str(junit),
            "--out",
            str(out),
        ]
    )
    assert code == 0 and out.read_text(encoding="utf-8").startswith("# Acceptance matrix")
