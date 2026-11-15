"""``aitaf report``: the report of a stored run from the command line (FR-31, FR-32, FR-39, NFR-01).

Runs the real chain on a fake-browser project: execute, diagnose, report. The PDF
renderer is replaced by a stub here; the real browser renderer has its own
integration test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fake_browser_project import DEFECT_TEST, ID_MUTATED_DOM, LOGIN_TEST, project

from aitaf.cli import main

ODD_TEST = "def test_odd(page):\n    raise RuntimeError('unexpected state')\n"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_PROVIDER", "LLM_CALL_CAP", "OPENAI_API_KEY", "LLM_MODEL", "LLM_CACHE_DIR"):
        monkeypatch.delenv(name, raising=False)


def run_chain(tmp_path: Path, *, diagnose: bool = True) -> None:
    scripts = project(
        tmp_path,
        {"test_defect": DEFECT_TEST, "test_odd": ODD_TEST, "test_login": LOGIN_TEST},
        ID_MUTATED_DOM,
    )
    db, evidence = str(tmp_path / "x.db"), str(tmp_path / "evidence")
    main(
        [
            "execute",
            "--scripts",
            str(scripts),
            "--base-url",
            "http://127.0.0.1:8765",
            "--db",
            db,
            "--evidence",
            evidence,
        ]
    )
    if diagnose:
        main(["diagnose", "--db", db, "--evidence", evidence])


def report(tmp_path: Path, *extra: str) -> int:
    return main(
        [
            "report",
            "--db",
            str(tmp_path / "x.db"),
            "--evidence",
            str(tmp_path / "evidence"),
            "--out",
            str(tmp_path / "out"),
            *extra,
        ]
    )


@pytest.mark.blackbox
def test_the_report_files_are_written_and_the_headline_figures_are_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_chain(tmp_path)
    capsys.readouterr()
    assert report(tmp_path) == 0
    out = capsys.readouterr().out
    for name in ("report.html", "report.md", "metrics.json", "metrics.csv"):
        assert (tmp_path / "out" / name).exists(), name
    assert "report.html" in out and "Pass rate" in out
    assert "Tests: 3 (0 passed, 3 failed, 0 error, 0 skipped)" in (
        tmp_path / "out" / "report.md"
    ).read_text(encoding="utf-8")


@pytest.mark.blackbox
def test_the_report_links_the_screenshots_of_the_failures(tmp_path: Path) -> None:
    run_chain(tmp_path)
    report(tmp_path)
    html = (tmp_path / "out" / "report.html").read_text(encoding="utf-8")
    assert "Screenshot of test" in html and "evidence/" in html
    assert list((tmp_path / "out" / "evidence").glob("*.png"))


@pytest.mark.blackbox
def test_labels_give_the_classification_accuracy(tmp_path: Path) -> None:
    run_chain(tmp_path)
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "tc_id,category\nTEST-DEFECT,assertion_defect\nTEST-ODD,environment\n", encoding="utf-8"
    )
    assert report(tmp_path, "--labels", str(labels)) == 0
    metrics = json.loads((tmp_path / "out" / "metrics.json").read_text(encoding="utf-8"))
    accuracy = next(m for m in metrics["metrics"] if m["key"] == "classification_accuracy")
    assert accuracy["value"] == 0.5


@pytest.mark.blackbox
def test_a_report_can_be_made_before_any_diagnosis(tmp_path: Path) -> None:
    run_chain(tmp_path, diagnose=False)
    assert report(tmp_path) == 0
    assert "not analysed" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")


@pytest.mark.whitebox
def test_the_pdf_option_uses_the_browser_renderer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_chain(tmp_path)
    calls: list[Path] = []

    def stub(html: Path, pdf: Path) -> None:
        calls.append(pdf)
        pdf.write_bytes(b"%PDF-1.4 stub")

    monkeypatch.setattr("aitaf.cli.render_html_to_pdf", stub)
    assert report(tmp_path, "--pdf") == 0
    assert calls == [tmp_path / "out" / "report.pdf"]


@pytest.mark.whitebox
def test_without_the_pdf_option_no_pdf_is_made(tmp_path: Path) -> None:
    run_chain(tmp_path)
    report(tmp_path)
    assert not (tmp_path / "out" / "report.pdf").exists()


@pytest.mark.whitebox
@pytest.mark.parametrize(
    "content",
    ["tc_id,category\nTC-1,network\n", "tc_id\nTC-1\n", "category,tc_id\nlocator\n", ""],
    ids=["bad-category", "missing-column", "short-row", "empty"],
)
def test_a_bad_labels_file_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str
) -> None:
    run_chain(tmp_path)
    labels = tmp_path / "labels.csv"
    labels.write_text(content, encoding="utf-8")
    capsys.readouterr()
    assert report(tmp_path, "--labels", str(labels)) == 1
    assert "labels" in capsys.readouterr().err.lower()


@pytest.mark.whitebox
def test_a_missing_labels_file_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_chain(tmp_path)
    capsys.readouterr()
    assert report(tmp_path, "--labels", str(tmp_path / "none.csv")) == 1
    assert "labels" in capsys.readouterr().err.lower()


@pytest.mark.whitebox
def test_a_database_without_results_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert report(tmp_path) == 1
    assert "aitaf execute" in capsys.readouterr().err


@pytest.mark.whitebox
def test_an_unknown_run_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_chain(tmp_path)
    capsys.readouterr()
    assert report(tmp_path, "--run", "no-such-run") == 1
    assert "no-such-run" in capsys.readouterr().err


@pytest.mark.whitebox
def test_the_rendering_time_is_stored_as_a_metric(tmp_path: Path) -> None:
    import sqlite3

    run_chain(tmp_path)
    report(tmp_path)
    with sqlite3.connect(tmp_path / "x.db") as conn:
        rows = conn.execute(
            "SELECT component, operation FROM metric_samples WHERE component = 'reporting_engine'"
        ).fetchall()
    assert rows == [("reporting_engine", "render")]
