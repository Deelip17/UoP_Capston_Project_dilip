"""Pre-rendered PNG charts for the Dashboard (FR-33).

Charts need matplotlib, an optional extra (``pip install -r requirements-report.txt``).
One hue (blue) on a light surface; every chart is also in the page's table, and the
page gives each image a text alternative. A run with no value for a metric leaves a gap.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aitaf.core.errors import ConfigError
from aitaf.dashboard.data import DashboardData

BLUE = "#2a78d6"
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e3e2de"

PASS_RATE_CHART = "pass_rate_trend.png"
QUALITY_CHART = "quality_trend.png"
COST_LATENCY_CHART = "cost_and_latency.png"
CHART_FILES = (PASS_RATE_CHART, QUALITY_CHART, COST_LATENCY_CHART)

_QUALITY_PANELS = (
    ("requirement_coverage_ratio", "Requirement coverage"),
    ("script_executability_rate", "Script executability"),
    ("healing_success_rate", "Healing success"),
    ("classification_accuracy", "Classification accuracy"),
)


def _plt() -> Any:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ConfigError("charts need matplotlib: pip install -r requirements-report.txt") from exc
    return plt


def _frame(ax: Any, title: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)


def _no_data(ax: Any) -> None:
    ax.text(0.5, 0.5, "no data", ha="center", va="center", color=MUTED, transform=ax.transAxes)


def _line(ax: Any, data: DashboardData, key: str, percent: bool = True) -> None:
    frame = data.frame
    values = frame[key] * 100 if percent else frame[key]
    if values.notna().sum() == 0:
        _no_data(ax)
    else:
        ax.plot(frame["n"], values, color=BLUE, linewidth=2, marker="o", markersize=6)
        ax.set_xticks(list(frame["n"]))
    if percent:
        ax.set_ylim(0, 105)
        ax.set_ylabel("%", color=MUTED, fontsize=8)


def _bars(ax: Any, data: DashboardData, key: str) -> None:
    frame = data.frame
    if frame[key].notna().sum() == 0:
        _no_data(ax)
        return
    ax.bar(frame["n"], frame[key].fillna(0), color=BLUE, width=0.5)
    ax.set_xticks(list(frame["n"]))
    top = float(frame[key].max())
    ax.set_ylim(0, top * 1.1 if top > 0 else 1)


def _save(fig: Any, path: Path) -> None:
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=SURFACE)
    _plt().close(fig)


def write_charts(data: DashboardData, out_dir: Path) -> list[Path]:
    """Write the three chart files into ``out_dir`` and return their paths."""
    plt = _plt()
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    _frame(ax, "Pass rate per run")
    _line(ax, data, "pass_rate")
    ax.set_xlabel("run number (oldest first)", color=MUTED, fontsize=8)
    _save(fig, out_dir / PASS_RATE_CHART)

    fig, axes = plt.subplots(2, 2, figsize=(6.4, 5.0))
    for ax, (key, title) in zip(axes.flat, _QUALITY_PANELS, strict=True):
        _frame(ax, title)
        _line(ax, data, key)
    _save(fig, out_dir / QUALITY_CHART)

    fig, (left, right) = plt.subplots(1, 2, figsize=(6.4, 3.0))
    _frame(left, "API cost per run (USD)")
    _bars(left, data, "api_cost_usd")
    _frame(right, "Generation latency, median (ms)")
    _bars(right, data, "generation_latency_ms_median")
    _save(fig, out_dir / COST_LATENCY_CHART)
    return [out_dir / name for name in CHART_FILES]
