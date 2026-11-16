"""Collect one row per stored run for the Dashboard (FR-33).

Every figure comes from :func:`aitaf.reporting.build_report`, so the Dashboard and the
run report cannot disagree. A metric that could not be computed stays missing (NaN in
the table, "n/a" on the page); it is never shown as zero.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from aitaf.core.storage import Repository
from aitaf.reporting import MetricValue, build_report

METRIC_KEYS = (
    "pass_rate",
    "requirement_coverage_ratio",
    "script_executability_rate",
    "healing_success_rate",
    "classification_accuracy",
    "generation_latency_ms_median",
    "api_cost_usd",
)
TREND_MIN_RUNS = 3


@dataclass
class DashboardData:
    """The run table plus the unit, label and basis of every metric column."""

    frame: pd.DataFrame
    metrics: dict[str, MetricValue] = field(default_factory=dict)

    @property
    def run_count(self) -> int:
        return len(self.frame)

    @property
    def has_trend(self) -> bool:
        return self.run_count >= TREND_MIN_RUNS

    def latest(self) -> pd.Series | None:
        return self.frame.iloc[-1] if self.run_count else None


def collect(
    repo: Repository,
    labels: Mapping[str, str] | None = None,
    source_run: str | None = None,
    last: int | None = None,
) -> DashboardData:
    """One row per run with stored results, oldest first (the last ``last`` if given)."""
    run_ids = repo.list_runs_with_results()
    if last is not None:
        run_ids = run_ids[-last:]
    rows: list[dict[str, object]] = []
    metrics: dict[str, MetricValue] = {}
    for position, run_id in enumerate(run_ids, start=1):
        report = build_report(repo, run_id, source_run, labels=labels)
        row: dict[str, object] = {
            "n": position,
            "run_id": run_id,
            "started_at": report.run.started_at,
            "provider": report.provider,
            "tests": report.total,
            "passed": report.passed,
            "failed": report.failed + report.errors,
        }
        by_key = {m.key: m for m in report.metrics}
        for key in METRIC_KEYS:
            metric = by_key[key]
            metrics.setdefault(key, metric)
            row[key] = metric.value
        rows.append(row)
    columns = ["n", "run_id", "started_at", "provider", "tests", "passed", "failed", *METRIC_KEYS]
    frame = pd.DataFrame(rows, columns=columns)
    frame[list(METRIC_KEYS)] = frame[list(METRIC_KEYS)].astype("float64")
    return DashboardData(frame=frame, metrics=metrics)
