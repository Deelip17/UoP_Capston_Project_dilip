"""Non-LLM latency samples (NFR-01).

NFR-01 asks for the time the framework itself spends, without waiting for a model. The
Reporting Engine's work (collect the data of a stored run, compute the metrics, render
HTML, Markdown, JSON and CSV) is repeated many times on one stored run, in this process,
and each repetition is timed. The first repetition is kept in the raw rows and flagged as
warm-up so the figures can exclude it openly.
"""

from __future__ import annotations

import csv
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from aitaf.core.errors import PersistenceError
from aitaf.core.storage import SqliteRepository
from aitaf.reporting import build_report, write_report


@dataclass(frozen=True)
class LatencySample:
    """One timed repetition of the report pipeline."""

    sample: int
    operation: str
    duration_ms: float
    warmup: bool


def measure_report_latency(db: Path | str, samples: int = 30) -> list[LatencySample]:
    """Time ``samples`` repetitions of build and write for the latest run with results."""
    if samples < 2:
        raise ValueError("at least two samples are needed (the first is warm-up)")
    repo = SqliteRepository(db)
    try:
        run_id = repo.latest_run_with_results()
        if run_id is None:
            raise PersistenceError("the database holds no test results")
        rows: list[LatencySample] = []
        for number in range(1, samples + 1):
            with tempfile.TemporaryDirectory() as folder:
                start = time.perf_counter()
                data = build_report(repo, run_id)
                write_report(data, Path(folder))
                elapsed = (time.perf_counter() - start) * 1000
            rows.append(
                LatencySample(number, "report_build_and_write", round(elapsed, 3), number == 1)
            )
        return rows
    finally:
        repo.close()


def write_latency_csv(rows: Sequence[LatencySample], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["sample", "operation", "duration_ms", "warmup"])
        for r in rows:
            writer.writerow([r.sample, r.operation, r.duration_ms, r.warmup])
    return target


def read_latency_csv(path: Path | str) -> list[LatencySample]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return [
            LatencySample(
                int(r["sample"]), r["operation"], float(r["duration_ms"]), r["warmup"] == "True"
            )
            for r in csv.DictReader(handle)
        ]
