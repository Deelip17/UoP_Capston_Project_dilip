"""Reporting Engine: one data model, an offline HTML report, Markdown, metrics and traceability.

Requirements: FR-31 (HTML report), FR-32 (Markdown and PDF from one model), FR-34
(traceability), FR-39 (Unit 6 metrics from stored data), NFR-01, NFR-29.
"""

from aitaf.reporting.builder import build_report, trace_for_requirement, trace_for_result
from aitaf.reporting.metrics import compute_metrics, percentile, provider_label
from aitaf.reporting.model import MetricValue, ReportData, ReportTest, TraceRow, format_value
from aitaf.reporting.render_html import PALETTE, render_html
from aitaf.reporting.render_markdown import render_markdown
from aitaf.reporting.writer import PdfRenderer, ReportFiles, write_report

__all__ = [
    "PALETTE",
    "MetricValue",
    "PdfRenderer",
    "ReportData",
    "ReportFiles",
    "ReportTest",
    "TraceRow",
    "build_report",
    "compute_metrics",
    "format_value",
    "percentile",
    "provider_label",
    "render_html",
    "render_markdown",
    "trace_for_requirement",
    "trace_for_result",
    "write_report",
]
