"""Report data model, traceability, HTML and Markdown renderers (FR-31, FR-32, FR-34, NFR-29).

One data model feeds both renderers, so the two files must show identical figures.
The HTML report must open offline without a server (no scripts, no external links, every
local link present on disk), put the summary first, and meet the review checklist of
NFR-29: text alternatives for screenshots, table captions and headers, contrast.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest
from pipeline_records import EXEC, SOURCE, analysis, audit, result, seeded_repo

from aitaf.core.errors import PersistenceError, ReportingError
from aitaf.reporting import (
    PALETTE,
    build_report,
    render_html,
    render_markdown,
    trace_for_requirement,
    trace_for_result,
    write_report,
)
from aitaf.reporting.model import format_value


@pytest.fixture
def data():  # type: ignore[no-untyped-def]
    return build_report(seeded_repo(), EXEC, SOURCE, labels={"TC-2": "locator"})


# ----------------------------------------------------------------------- model


@pytest.mark.blackbox
def test_the_report_lists_every_result_with_its_requirement_script_and_analysis(data) -> None:  # type: ignore[no-untyped-def]
    assert [t.tc_id for t in data.tests] == ["TC-1", "TC-2", "TC-3", "TC-5"]
    first, second, third, fifth = data.tests
    assert (first.requirement_id, first.script_path) == ("R1", "tests/test_tc-1.py")
    assert second.analysis is not None and second.analysis.category == "locator"
    assert third.analysis is not None and third.analysis.source == "llm"
    assert first.analysis is None
    assert fifth.requirement_id == "" and fifth.title == "TC-5"
    assert second.healed is True and third.healed is False


@pytest.mark.blackbox
def test_counts_and_the_headline_numbers(data) -> None:  # type: ignore[no-untyped-def]
    assert (data.total, data.passed, data.failed, data.errors, data.skipped) == (4, 1, 1, 1, 1)
    assert data.provider == "mock"
    assert data.source_run_id == SOURCE


@pytest.mark.blackbox
def test_the_source_run_defaults_to_the_latest_run_with_requirements() -> None:
    assert build_report(seeded_repo(), EXEC).source_run_id == SOURCE


@pytest.mark.whitebox
def test_an_unknown_run_is_rejected() -> None:
    with pytest.raises(PersistenceError):
        build_report(seeded_repo(), "no-such-run")


@pytest.mark.blackbox
def test_the_full_chain_is_available_for_a_result_and_in_reverse(data) -> None:  # type: ignore[no-untyped-def]
    """FR-34: requirement, test case, script, execution, failure and report in one place."""
    row = trace_for_result(data, "res-TC-2")
    assert row is not None
    assert (row.requirement_id, row.tc_id, row.script_path, row.status) == (
        "R1",
        "TC-2",
        "tests/test_tc-2.py",
        "failed",
    )
    assert row.analysis_category == "locator" and row.cluster_id == "CL-0123abcd"
    assert [r.tc_id for r in trace_for_requirement(data, "R1")] == ["TC-1", "TC-2"]
    assert trace_for_requirement(data, "R4") == []
    assert trace_for_result(data, "res-nope") is None


# ------------------------------------------------------------------------ html


def html_of(data) -> str:  # type: ignore[no-untyped-def]
    return render_html(data)


@pytest.mark.blackbox
def test_the_html_is_a_complete_document_with_the_summary_first(data) -> None:  # type: ignore[no-untyped-def]
    html = html_of(data)
    assert html.startswith("<!DOCTYPE html>") and '<html lang="en">' in html
    order = [html.index(f'id="{name}"') for name in ("summary", "metrics", "results", "failures")]
    assert order == sorted(order)
    assert "<h1>" in html and "<title>" in html


@pytest.mark.blackbox
def test_each_failure_shows_its_cause_next_step_screenshot_and_log_link(data) -> None:  # type: ignore[no-untyped-def]
    html = html_of(data)
    assert "Cause for TC-2." in html and "Next step for TC-2." in html
    assert 'src="evidence/b.png"' in html
    assert 'alt="Screenshot of test TC-2 at failure"' in html
    assert 'href="evidence/b.html"' in html and 'href="logs/res-TC-2.txt"' in html


@pytest.mark.blackbox
def test_the_html_opens_offline_no_scripts_no_external_links(data) -> None:  # type: ignore[no-untyped-def]
    html = html_of(data)
    assert "<script" not in html.lower()
    for value in re.findall(r'(?:src|href)="([^"]*)"', html):
        assert not re.match(r"^(?:[a-z]+:)?//", value) and ":" not in value.split("/")[0], value


@pytest.mark.blackbox
def test_text_that_comes_from_tests_cannot_inject_markup() -> None:
    repo = seeded_repo()
    repo.add_result(
        result(
            "TC-9",
            "failed",
            log="<script>alert(1)</script>",
            screenshot='x" onerror="alert(1)',
        )
    )
    html = render_html(build_report(repo, EXEC, SOURCE))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert 'onerror="alert(1)' not in html


@pytest.mark.blackbox
def test_the_review_checklist_for_non_technical_readers_is_met(data) -> None:  # type: ignore[no-untyped-def]
    """NFR-29: summary first, drill-down second, text alternatives, labelled tables."""
    html = html_of(data)
    assert html.count("<img") == html.count('alt="') >= 1
    assert re.search(r"<table>\s*<caption>", html)
    assert '<th scope="col">' in html and "<details>" in html
    for word in ("PASSED", "FAILED", "ERROR", "SKIPPED"):
        assert word in html  # status is written, not only coloured


def luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.blackbox
@pytest.mark.parametrize(
    ("foreground", "background"),
    [
        ("text", "background"),
        ("muted", "background"),
        ("link", "background"),
        ("badge_text", "pass"),
        ("badge_text", "fail"),
        ("badge_text", "error"),
        ("badge_text", "skip"),
    ],
)
def test_every_colour_pair_meets_the_AA_contrast_ratio(foreground: str, background: str) -> None:
    assert contrast(PALETTE[foreground], PALETTE[background]) >= 4.5


@pytest.mark.whitebox
def test_the_provider_and_the_ai_label_are_stated(data) -> None:  # type: ignore[no-untyped-def]
    html = html_of(data)
    assert "Provider: mock" in html
    assert "AI-generated" in html  # TC-3's explanation came from the model step


@pytest.mark.whitebox
def test_a_report_with_no_failures_says_so() -> None:
    repo = seeded_repo()
    clean = build_report(repo, EXEC, SOURCE)
    clean.tests = [t for t in clean.tests if t.status == "passed"]
    clean.analyses = []
    html = render_html(clean)
    assert "No failed tests" in html
    assert "AI-generated" not in html


# -------------------------------------------------------------------- markdown


@pytest.mark.blackbox
def test_markdown_and_html_show_identical_figures(data) -> None:  # type: ignore[no-untyped-def]
    """FR-32: both files come from one data model."""
    html, md = html_of(data), render_markdown(data)
    for metric in data.metrics:
        text = format_value(metric)
        assert text in html and text in md, metric.key
    summary = "Tests: 4 (1 passed, 1 failed, 1 error, 1 skipped)"
    assert summary in html and summary in md
    for test in data.tests:
        assert test.tc_id in html and test.tc_id in md


@pytest.mark.blackbox
def test_markdown_has_tables_images_and_the_failure_analysis(data) -> None:  # type: ignore[no-untyped-def]
    md = render_markdown(data)
    assert md.startswith("# ") and "\n## Summary" in md
    assert "| Test case |" in md and "|---" in md
    assert "![Screenshot of test TC-2 at failure](evidence/b.png)" in md
    assert "Cause for TC-2." in md and "Next step for TC-2." in md


@pytest.mark.whitebox
def test_pipes_and_newlines_in_cells_do_not_break_the_markdown_table() -> None:
    repo = seeded_repo()
    repo.add_result(result("TC-9", "failed", error_text="a | b\nc"))
    md = render_markdown(build_report(repo, EXEC, SOURCE))
    row = next(line for line in md.splitlines() if "TC-9" in line and line.startswith("|"))
    assert row.count("|") == next(
        line for line in md.splitlines() if line.startswith("| Test case |")
    ).count("|")


@pytest.mark.whitebox
@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (None, "ratio", "n/a"),
        (0.5, "ratio", "50.0%"),
        (200.0, "ms", "200 ms"),
        (0.0055, "usd", "$0.0055"),
    ],
)
def test_figures_are_formatted_in_one_place(value: float | None, unit: str, expected: str) -> None:
    from aitaf.reporting.model import MetricValue

    assert format_value(MetricValue("k", "L", value, unit, "b")) == expected


# ----------------------------------------------------------------- write_report


def evidence_dir(tmp_path: Path) -> Path:
    folder = tmp_path / "evidence_in"
    folder.mkdir()
    for name in ("a.png", "b.png", "a.html", "b.html"):
        (folder / name).write_bytes(b"data " + name.encode())
    return folder


@pytest.mark.blackbox
def test_write_report_creates_the_files_and_every_local_link_resolves(
    data,
    tmp_path: Path,  # type: ignore[no-untyped-def]
) -> None:
    files = write_report(data, tmp_path / "out", evidence_dir(tmp_path))
    for path in (files.html, files.markdown, files.metrics_json, files.metrics_csv):
        assert path.exists()
    for page in (files.html, files.markdown):
        text = page.read_text(encoding="utf-8")
        for target in re.findall(r'(?:src|href)="([^"]+)"|\]\(([^)\s]+)\)', text):
            link = target[0] or target[1]
            assert (files.html.parent / link).exists(), link


@pytest.mark.blackbox
def test_the_log_of_every_failed_test_is_written_and_linked(
    data,
    tmp_path: Path,  # type: ignore[no-untyped-def]
) -> None:
    files = write_report(data, tmp_path / "out", evidence_dir(tmp_path))
    log = tmp_path / "out" / "logs" / "res-TC-2.txt"
    assert log.read_text(encoding="utf-8").strip() == "TC-2 failed"
    assert files.html.read_text(encoding="utf-8").count("logs/res-TC-2.txt") >= 1


@pytest.mark.blackbox
def test_the_metrics_are_exported_as_json_and_csv(data, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """FR-39: metrics exported as CSV for the appendix."""
    files = write_report(data, tmp_path / "out", None)
    exported = json.loads(files.metrics_json.read_text(encoding="utf-8"))
    assert exported["provider"] == "mock" and exported["run_id"] == EXEC
    assert {m["key"] for m in exported["metrics"]} == {m.key for m in data.metrics}
    with files.metrics_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["key"] for r in rows] == [m.key for m in data.metrics]
    assert set(rows[0]) == {"key", "label", "value", "unit", "basis", "provider"}
    assert {r["provider"] for r in rows} == {"mock"}


@pytest.mark.whitebox
def test_evidence_outside_the_evidence_directory_is_never_copied_or_linked(
    tmp_path: Path,
) -> None:
    repo = seeded_repo()
    repo.add_result(
        result("TC-9", "failed", screenshot="../secret.png", dom_snapshot="..\\secret.html")
    )
    (tmp_path / "secret.png").write_bytes(b"secret")
    data = build_report(repo, EXEC, SOURCE)
    files = write_report(data, tmp_path / "out", evidence_dir(tmp_path))
    assert not (tmp_path / "out" / "secret.png").exists()
    page = files.html.read_text(encoding="utf-8")
    assert "secret" not in page and "../" not in page


@pytest.mark.whitebox
def test_missing_evidence_files_are_not_linked(data, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    files = write_report(data, tmp_path / "out", tmp_path / "empty")
    assert "<img" not in files.html.read_text(encoding="utf-8")


# -------------------------------------------------------------------------- pdf


@pytest.mark.blackbox
def test_the_pdf_is_made_by_the_injected_renderer_from_the_html(
    data,
    tmp_path: Path,  # type: ignore[no-untyped-def]
) -> None:
    calls: list[tuple[Path, Path]] = []

    def renderer(html: Path, pdf: Path) -> None:
        calls.append((html, pdf))
        pdf.write_bytes(b"%PDF-1.4 stub")

    files = write_report(data, tmp_path / "out", None, pdf_renderer=renderer)
    assert files.pdf == tmp_path / "out" / "report.pdf" and files.pdf.exists()
    assert calls == [(files.html, files.pdf)]


@pytest.mark.whitebox
def test_without_a_renderer_there_is_no_pdf(data, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    assert write_report(data, tmp_path / "out", None).pdf is None


@pytest.mark.whitebox
def test_a_renderer_that_fails_or_writes_nothing_is_reported(data, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    def broken(html: Path, pdf: Path) -> None:
        raise OSError("no browser")

    with pytest.raises(ReportingError, match="PDF"):
        write_report(data, tmp_path / "a", None, pdf_renderer=broken)
    with pytest.raises(ReportingError, match="PDF"):
        write_report(data, tmp_path / "b", None, pdf_renderer=lambda html, pdf: None)


@pytest.mark.whitebox
def test_unused_helpers_stay_importable() -> None:
    assert analysis("TC-1", "locator").category == "locator" and audit("c", EXEC, True).mock
