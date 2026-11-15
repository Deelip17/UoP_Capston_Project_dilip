"""The single report data model both renderers read (FR-31, FR-32, FR-34).

Everything a report shows lives here; the HTML and Markdown renderers only format it,
so the two files cannot disagree. Figures are formatted in one function
(:func:`format_value`) for the same reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from aitaf.core.models import FailureAnalysis, HealingEvent, Run

_ratio_units = {"ratio"}


@dataclass(frozen=True)
class MetricValue:
    """One computed metric with its unit and the basis it was counted on."""

    key: str
    label: str
    value: float | None
    unit: str
    basis: str


def format_value(metric: MetricValue) -> str:
    """Human text for a metric value; ``n/a`` when it could not be computed."""
    if metric.value is None:
        return "n/a"
    if metric.unit in _ratio_units:
        return f"{metric.value * 100:.1f}%"
    if metric.unit == "ms":
        return f"{metric.value:.0f} ms"
    if metric.unit == "usd":
        return f"${metric.value:.4f}"
    return f"{metric.value:g}"


@dataclass(frozen=True)
class TraceRow:
    """The chain requirement, test case, script, execution, failure for one result (FR-34)."""

    result_id: str
    tc_id: str
    requirement_id: str
    requirement_ref: str
    script_path: str
    status: str
    analysis_category: str
    cluster_id: str


@dataclass
class ReportTest:
    """One executed test as the report shows it."""

    result_id: str
    tc_id: str
    title: str
    requirement_id: str
    script_path: str
    status: str
    duration_ms: int
    attempts: int
    healed: bool
    screenshot: str
    dom_snapshot: str
    log: str
    analysis: FailureAnalysis | None = None


@dataclass
class ReportData:
    """Everything one report shows."""

    title: str
    run: Run
    source_run_id: str | None
    generated_at: datetime
    provider: str
    tests: list[ReportTest] = field(default_factory=list)
    healing_events: list[HealingEvent] = field(default_factory=list)
    analyses: list[FailureAnalysis] = field(default_factory=list)
    clusters: dict[str, list[str]] = field(default_factory=dict)
    metrics: list[MetricValue] = field(default_factory=list)
    trace: list[TraceRow] = field(default_factory=list)

    def _count(self, status: str) -> int:
        return sum(1 for test in self.tests if test.status == status)

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def passed(self) -> int:
        return self._count("passed")

    @property
    def failed(self) -> int:
        return self._count("failed")

    @property
    def errors(self) -> int:
        return self._count("error")

    @property
    def skipped(self) -> int:
        return self._count("skipped")

    @property
    def summary_line(self) -> str:
        return (
            f"Tests: {self.total} ({self.passed} passed, {self.failed} failed, "
            f"{self.errors} error, {self.skipped} skipped)"
        )

    @property
    def has_ai_text(self) -> bool:
        return any(t.analysis is not None and t.analysis.source == "llm" for t in self.tests)
