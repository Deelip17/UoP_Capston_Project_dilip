"""The Dashboard page: one offline HTML file, summary first, then charts (FR-33, NFR-29).

No scripts and no external links. Every figure is also written as text, every chart has a
text alternative, tables have captions, and "n/a" is shown for a metric that could not be
computed. The provider (mock or live) is shown beside each run so the two are never mixed.
"""

from __future__ import annotations

import math
from html import escape

import pandas as pd

from aitaf.dashboard.charts import COST_LATENCY_CHART, PASS_RATE_CHART, QUALITY_CHART
from aitaf.dashboard.data import METRIC_KEYS, TREND_MIN_RUNS, DashboardData
from aitaf.reporting import MetricValue, format_value
from aitaf.reporting.render_html import PALETTE

_TILES = (
    "pass_rate",
    "requirement_coverage_ratio",
    "script_executability_rate",
    "healing_success_rate",
    "classification_accuracy",
    "generation_latency_ms_median",
    "api_cost_usd",
)
_ALT = {
    PASS_RATE_CHART: "Line chart of the pass rate of each run, oldest run first.",
    QUALITY_CHART: (
        "Four small line charts over the runs: requirement coverage, script executability, "
        "healing success and classification accuracy, in percent."
    ),
    COST_LATENCY_CHART: (
        "Two bar charts over the runs: API cost in US dollars and median generation latency "
        "in milliseconds."
    ),
}


def _css() -> str:
    p = PALETTE
    return (
        f"body{{font-family:Arial,Helvetica,sans-serif;max-width:64rem;margin:1.5rem auto;"
        f"padding:0 1rem;color:{p['text']};background:{p['background']};line-height:1.45}}"
        f"h1,h2{{margin-top:1.6rem}}"
        f".tiles{{display:flex;flex-wrap:wrap;gap:.6rem;padding:0;list-style:none}}"
        f".tile{{border:1px solid {p['rule']};padding:.5rem .8rem;min-width:9.5rem}}"
        f".tile b{{display:block;font-size:1.5rem}}"
        f".muted{{color:{p['muted']}}}"
        f"table{{border-collapse:collapse;width:100%;margin:.6rem 0}}"
        f"caption{{text-align:left;font-weight:bold;padding:.3rem 0}}"
        f"th,td{{border:1px solid {p['rule']};padding:.35rem .5rem;text-align:left}}"
        f"figure{{margin:1rem 0}}img{{max-width:100%;border:1px solid {p['rule']}}}"
        f".note{{border-left:.3rem solid {p['link']};padding:.2rem .8rem}}"
    )


def _text(metric: MetricValue, value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return format_value(MetricValue(metric.key, metric.label, value, metric.unit, metric.basis))


def _tiles(data: DashboardData) -> str:
    latest = data.latest()
    if latest is None:
        return ""
    items = []
    for key in _TILES:
        metric = data.metrics[key]
        items.append(
            f'<li class="tile"><span class="muted">{escape(metric.label)}</span>'
            f"<b>{escape(_text(metric, latest[key]))}</b></li>"
        )
    return (
        f"<h2>Latest run</h2><p>Run {escape(str(latest['run_id']))}, provider "
        f"<b>{escape(str(latest['provider']))}</b>.</p>"
        + '<ul class="tiles">'
        + "".join(items)
        + "</ul>"
    )


def _table(data: DashboardData) -> str:
    head = ["#", "Run", "Provider", "Tests", "Passed", "Failed"] + [
        data.metrics[key].label for key in METRIC_KEYS
    ]
    rows = []
    for _, row in data.frame.iterrows():
        cells = [
            str(row["n"]),
            str(row["run_id"]),
            str(row["provider"]),
            str(row["tests"]),
            str(row["passed"]),
            str(row["failed"]),
        ] + [_text(data.metrics[key], row[key]) for key in METRIC_KEYS]
        rows.append("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in cells) + "</tr>")
    header = "".join(f'<th scope="col">{escape(h)}</th>' for h in head)
    return (
        "<table><caption>All stored runs, oldest first</caption>"
        f"<thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _trend_note(data: DashboardData) -> str:
    if not data.has_trend:
        return (
            f'<p class="note">The trend needs at least {TREND_MIN_RUNS} runs; '
            f"{data.run_count} stored so far. Charts below show what exists.</p>"
        )
    return ""


def _basis(data: DashboardData) -> str:
    items = "".join(
        f"<li><b>{escape(data.metrics[key].label)}</b>: {escape(data.metrics[key].basis)}</li>"
        for key in METRIC_KEYS
    )
    return f"<h2>How each number is counted</h2><ul>{items}</ul>"


def render_dashboard(data: DashboardData, chart_dir: str = "charts") -> str:
    """The full page; ``chart_dir`` is the folder (relative to the page) holding the PNGs."""
    if data.run_count == 0:
        body = "<p>No test results are stored yet. Run <code>aitaf execute</code> first.</p>"
    else:
        images = "".join(
            f'<figure><img src="{escape(chart_dir)}/{name}" alt="{escape(alt)}">'
            f'<figcaption class="muted">{escape(alt)}</figcaption></figure>'
            for name, alt in _ALT.items()
        )
        body = (
            _tiles(data)
            + "<h2>Trend over runs</h2>"
            + _trend_note(data)
            + images
            + "<h2>Run table</h2>"
            + _table(data)
            + _basis(data)
            + '<p class="muted">Coverage, executability and cost use the latest analysis run '
            "as source. Mock-provider figures describe the pipeline, not model quality.</p>"
        )
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>AITAF dashboard</title><style>{_css()}</style></head><body>"
        "<h1>AITAF dashboard</h1>"
        '<p class="muted">Summary first, charts second, every figure also in the table.</p>'
        f"{body}</body></html>"
    )


def to_csv(frame: pd.DataFrame) -> str:
    """The run table as CSV text (the raw numbers behind the page)."""
    return str(frame.to_csv(index=False))
