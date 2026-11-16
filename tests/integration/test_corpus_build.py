"""The failure corpus built for real in Chromium (FR-27, FR-28, objective O4).

Needs Chromium; excluded from the default run (marker ``integration``).
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from aitaf.evaluation.corpus import FAILURES_FILE, LABELS_FILE, MIN_FAILURES, build_corpus

pytestmark = [pytest.mark.integration, pytest.mark.blackbox]


def test_the_corpus_has_at_least_forty_failures_and_blank_labels(tmp_path: Path) -> None:
    info = build_corpus(tmp_path / "corpus")
    assert info.failures >= MIN_FAILURES
    with (info.folder / LABELS_FILE).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == info.failures and all(r["category"] == "" for r in rows)
    with (info.folder / FAILURES_FILE).open(encoding="utf-8", newline="") as handle:
        failures = list(csv.DictReader(handle))
    assert {r["error_type"] for r in failures} >= {"LookupError", "AssertionError", "TimeoutError"}
    with pytest.raises(FileExistsError):
        build_corpus(info.folder)  # built once
