"""Dashboard: a static HTML page with Pandas aggregation and pre-rendered charts.

Requirements: FR-33 (pass rate, healing, accuracy, coverage, executability, cost, latency
and a trend over at least three stored runs), NFR-29 (readable by non-technical readers).
It is a wiring package like ``evaluation``: it reads the stored runs through the
Reporting Engine's metrics so its numbers equal the run report's.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aitaf.dashboard.charts import CHART_FILES, write_charts
from aitaf.dashboard.data import TREND_MIN_RUNS, DashboardData, collect
from aitaf.dashboard.render import render_dashboard, to_csv

HTML_FILE = "dashboard.html"
CSV_FILE = "dashboard.csv"
CHART_DIR = "charts"


@dataclass(frozen=True)
class DashboardFiles:
    html: Path
    csv: Path
    charts: list[Path]


def write_dashboard(data: DashboardData, out_dir: Path) -> DashboardFiles:
    """Write the page, its CSV and (when there are runs) the charts into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    charts = write_charts(data, out_dir / CHART_DIR) if data.run_count else []
    html = out_dir / HTML_FILE
    html.write_text(render_dashboard(data, CHART_DIR), encoding="utf-8")
    csv = out_dir / CSV_FILE
    csv.write_text(to_csv(data.frame), encoding="utf-8", newline="")
    return DashboardFiles(html=html, csv=csv, charts=charts)


__all__ = [
    "CHART_FILES",
    "TREND_MIN_RUNS",
    "DashboardData",
    "DashboardFiles",
    "collect",
    "render_dashboard",
    "write_charts",
    "write_dashboard",
]
