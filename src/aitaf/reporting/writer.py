"""Write the report files: HTML, Markdown, metrics, logs, evidence (FR-31, FR-32, FR-39).

The output folder is self-contained: screenshots and page snapshots are copied next to
the report (only files that really exist inside the evidence directory, with safe
names), every failed test gets its log written to ``logs/``, and every link in the
HTML and Markdown is relative and resolves. The PDF is made by an injected renderer so
this package needs no browser library.
"""

from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aitaf.core.errors import ReportingError
from aitaf.reporting.model import ReportData, format_value
from aitaf.reporting.render_html import render_html, safe_name
from aitaf.reporting.render_markdown import render_markdown

PdfRenderer = Callable[[Path, Path], None]


@dataclass(frozen=True)
class ReportFiles:
    """Paths of the files written for one report."""

    html: Path
    markdown: Path
    metrics_json: Path
    metrics_csv: Path
    pdf: Path | None = None


def _copy_evidence(data: ReportData, evidence_dir: Path | None, out: Path) -> set[str]:
    """Copy the screenshots and snapshots the report refers to; return the names copied."""
    copied: set[str] = set()
    if evidence_dir is None or not evidence_dir.is_dir():
        return copied
    target = out / "evidence"
    for test in data.tests:
        for name in (test.screenshot, test.dom_snapshot):
            source = evidence_dir / name if safe_name(name) else None
            if source is not None and source.is_file() and name not in copied:
                target.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target / name)
                copied.add(name)
    return copied


def _metrics_files(data: ReportData, out: Path) -> tuple[Path, Path]:
    json_path, csv_path = out / "metrics.json", out / "metrics.csv"
    payload = {
        "run_id": data.run.run_id,
        "source_run_id": data.source_run_id,
        "provider": data.provider,
        "generated_at": data.generated_at.isoformat(),
        "metrics": [
            {"key": m.key, "label": m.label, "value": m.value, "unit": m.unit, "basis": m.basis}
            for m in data.metrics
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["key", "label", "value", "unit", "basis", "provider"])
        for m in data.metrics:
            raw = "" if m.value is None else repr(m.value)
            writer.writerow([m.key, m.label, raw, m.unit, m.basis, data.provider])
    return json_path, csv_path


def write_report(
    data: ReportData,
    out_dir: Path | str,
    evidence_dir: Path | None = None,
    pdf_renderer: PdfRenderer | None = None,
) -> ReportFiles:
    """Write the whole report into ``out_dir`` and return the file paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    available = _copy_evidence(data, evidence_dir, out)
    logs = out / "logs"
    for test in data.tests:
        if test.status in ("failed", "error") and safe_name(test.result_id):
            logs.mkdir(exist_ok=True)
            (logs / f"{test.result_id}.txt").write_text(
                test.log.rstrip() + "\n", encoding="utf-8", newline="\n"
            )
    html_path, md_path = out / "report.html", out / "report.md"
    html_path.write_text(render_html(data, available), encoding="utf-8", newline="\n")
    md_path.write_text(render_markdown(data, available), encoding="utf-8", newline="\n")
    json_path, csv_path = _metrics_files(data, out)

    pdf_path: Path | None = None
    if pdf_renderer is not None:
        pdf_path = out / "report.pdf"
        try:
            pdf_renderer(html_path, pdf_path)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ReportingError(f"the PDF could not be produced: {exc}") from exc
        if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
            raise ReportingError("the PDF could not be produced: the renderer wrote no file")
    return ReportFiles(html_path, md_path, json_path, csv_path, pdf_path)


__all__ = ["PdfRenderer", "ReportFiles", "format_value", "write_report"]
