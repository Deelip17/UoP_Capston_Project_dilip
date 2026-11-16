"""Dashboard: one row per run, an offline page, charts and the CLI command (FR-33, NFR-29).

Expected values are worked out by hand from the seeded records: the execution run
``run-exec`` has one pass, one failure, one error and one skipped test (pass rate 1/3).
Two more runs are added to it so a trend over three runs exists.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pipeline_records import EXEC, SOURCE, result, run, seeded_repo

from aitaf.cli import main
from aitaf.core.storage import InMemoryRepository, SqliteRepository
from aitaf.dashboard import (
    CHART_FILES,
    DashboardData,
    collect,
    render_dashboard,
    write_dashboard,
)
from aitaf.reporting import build_report


def three_runs() -> InMemoryRepository:
    repo = seeded_repo()
    for index, statuses in enumerate((("passed", "passed"), ("passed", "failed")), start=1):
        run_id = f"run-extra-{index}"
        repo.create_run(run(run_id))
        for tc_id, status in zip(("TC-1", "TC-2"), statuses, strict=True):
            repo.add_result(result(tc_id, status, run_id, result_id=f"{run_id}-{tc_id}"))
    return repo


@pytest.mark.blackbox
def test_one_row_per_run_with_results_oldest_first() -> None:
    data = collect(three_runs())
    assert list(data.frame["run_id"]) == [EXEC, "run-extra-1", "run-extra-2"]
    assert list(data.frame["n"]) == [1, 2, 3]
    assert data.run_count == 3 and data.has_trend


@pytest.mark.blackbox
def test_the_pass_rate_column_is_worked_out_per_run() -> None:
    frame = collect(three_runs()).frame
    assert list(frame["pass_rate"]) == pytest.approx([1 / 3, 1.0, 0.5])
    assert list(frame["passed"]) == [1, 2, 1]
    assert list(frame["failed"]) == [2, 0, 1]


@pytest.mark.blackbox
def test_dashboard_figures_equal_the_run_report() -> None:
    repo = three_runs()
    latest = collect(repo).frame.iloc[0]
    report = {m.key: m.value for m in build_report(repo, EXEC).metrics}
    assert latest["requirement_coverage_ratio"] == report["requirement_coverage_ratio"] == 0.5
    assert latest["healing_success_rate"] == report["healing_success_rate"] == 0.5


@pytest.mark.whitebox
def test_a_metric_that_cannot_be_computed_is_missing_not_zero() -> None:
    frame = collect(three_runs()).frame
    assert frame["classification_accuracy"].isna().all()


@pytest.mark.whitebox
def test_last_keeps_only_the_newest_runs() -> None:
    data = collect(three_runs(), last=2)
    assert list(data.frame["run_id"]) == ["run-extra-1", "run-extra-2"]


@pytest.mark.whitebox
def test_the_trend_needs_three_runs() -> None:
    data = collect(seeded_repo())
    assert data.run_count == 1 and not data.has_trend
    assert "needs at least 3 runs" in render_dashboard(data)


@pytest.mark.blackbox
def test_the_page_shows_summary_table_basis_and_text_alternatives() -> None:
    page = render_dashboard(collect(three_runs()))
    assert page.index("Latest run") < page.index("Trend over runs") < page.index("Run table")
    assert page.count("<img ") == 3 and page.count(' alt="') == 3
    assert "<caption>All stored runs, oldest first</caption>" in page
    assert "How each number is counted" in page
    assert "n/a" in page  # classification accuracy has no labels
    assert 'lang="en"' in page


@pytest.mark.whitebox
def test_the_page_is_offline_and_escapes_run_text() -> None:
    repo = seeded_repo()
    repo.create_run(run("run-<b>x"))
    repo.add_result(result("TC-1", "passed", "run-<b>x", result_id="x1"))
    page = render_dashboard(collect(repo))
    assert "<script" not in page and "http://" not in page and "https://" not in page
    assert "run-&lt;b&gt;x" in page and "run-<b>x" not in page


@pytest.mark.whitebox
def test_the_provider_is_shown_for_each_run() -> None:
    page = render_dashboard(collect(three_runs()))
    assert re.search(r"<td>mock</td>", page) or "<td>none</td>" in page


@pytest.mark.whitebox
def test_no_stored_results_gives_a_plain_message() -> None:
    data = collect(InMemoryRepository())
    assert data.run_count == 0
    assert "No test results are stored yet" in render_dashboard(data)


@pytest.mark.blackbox
def test_write_dashboard_creates_page_csv_and_charts(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    files = write_dashboard(collect(three_runs()), tmp_path)
    assert files.html.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert files.csv.read_text(encoding="utf-8").splitlines()[0].startswith("n,run_id")
    assert [p.name for p in files.charts] == list(CHART_FILES)
    for chart in files.charts:
        assert chart.read_bytes().startswith(b"\x89PNG")


@pytest.mark.whitebox
def test_charts_still_draw_when_every_value_is_missing(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    repo = InMemoryRepository()
    repo.create_run(run("only"))
    repo.add_result(result("TC-1", "skipped", "only", result_id="o1"))
    files = write_dashboard(collect(repo), tmp_path)
    assert len(files.charts) == 3


@pytest.mark.whitebox
def test_missing_matplotlib_is_a_configuration_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aitaf.core.errors import ConfigError
    from aitaf.dashboard import charts

    monkeypatch.setitem(__import__("sys").modules, "matplotlib", None)
    with pytest.raises(ConfigError, match="matplotlib"):
        charts.write_charts(collect(three_runs()), tmp_path)


@pytest.mark.blackbox
def test_cli_dashboard_reads_a_database_and_writes_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("matplotlib")
    db = tmp_path / "d.db"
    repo = SqliteRepository(db)
    for index in range(3):
        run_id = f"run-{index}"
        repo.create_run(run(run_id))
        repo.add_result(result("TC-1", "passed", run_id, result_id=f"r{index}"))
    repo.close()
    out = tmp_path / "dash"
    assert main(["dashboard", "--db", str(db), "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "3 run(s) with results" in printed and "needs at least 3" not in printed
    assert (out / "dashboard.html").exists() and (out / "charts" / CHART_FILES[0]).exists()


@pytest.mark.whitebox
def test_collect_returns_a_dashboard_data_with_every_metric_described() -> None:
    data = collect(three_runs())
    assert isinstance(data, DashboardData)
    for metric in data.metrics.values():
        assert metric.label and metric.basis


@pytest.mark.whitebox
def test_the_source_run_is_not_treated_as_an_execution_run() -> None:
    assert SOURCE not in collect(three_runs()).frame["run_id"].tolist()
