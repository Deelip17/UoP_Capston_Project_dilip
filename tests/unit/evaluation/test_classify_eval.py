"""Classification evaluation against the author's labels (FR-27, FR-28, NFR-15, objective O4).

The scorer must refuse unlabelled, partial or unknown labels, must refuse a corpus the
analyzer has already seen, and must compute accuracy from the rows alone. The corpus
database here is built by hand (no browser); the real-browser build is an integration test.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aitaf.core.errors import ValidationError
from aitaf.core.logging import set_run_id
from aitaf.core.models import Run, RunStatus, TestResult
from aitaf.core.storage import SqliteRepository
from aitaf.diagnosis import FailureAnalyzer
from aitaf.evaluation.classify_eval import (
    ClassificationRow,
    agreement,
    classification_figures,
    confusion,
    per_category,
    read_labels,
    read_rows_csv,
    run_classification,
    write_rows_csv,
)

RUN = "corpus-run"
KINDS = [
    ("LookupError", "no locator strategy matched for login_submit on page shop", "locator"),
    ("AssertionError", "assert 'Sign in' == 'Log in'", "assertion_defect"),
    ("TimeoutError", "Page.wait_for_selector: Timeout 500ms exceeded.", "timing_flaky"),
    ("Error", "Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:1/", "environment"),
]


def make_corpus(tmp_path: Path, count: int = 44) -> tuple[Path, dict[str, str]]:
    db = tmp_path / "corpus.db"
    repo = SqliteRepository(db)
    repo.create_run(
        Run(
            run_id=RUN,
            started_at=datetime.now(UTC),
            status=RunStatus.COMPLETED,
            provider="mock",
            environment="test",
        )
    )
    truth: dict[str, str] = {}
    for n in range(count):
        error_type, text, category = KINDS[n % len(KINDS)]
        tc = f"F{n + 1:03d}"
        truth[tc] = category
        repo.add_result(
            TestResult(
                result_id=f"R{n}",
                run_id=RUN,
                tc_id=tc,
                status="failed",
                duration_ms=5,
                nodeid=f"tests/test_case_{n:03d}.py::test_case_{n:03d}",
                error_type=error_type,
                error_text=text,
            )
        )
    repo.close()
    return db, truth


def write_labels(path: Path, labels: dict[str, str]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["tc_id", "category"])
        writer.writerows(labels.items())
    return path


@pytest.mark.blackbox
def test_rules_are_scored_against_the_labels_and_the_corpus_is_left_untouched(
    tmp_path: Path,
) -> None:
    db, truth = make_corpus(tmp_path)
    rows = run_classification(db, RUN, write_labels(tmp_path / "labels.csv", truth))
    assert len(rows) == 44
    assert all(r.correct for r in rows)  # the labels agree with the obvious categories
    assert {r.source for r in rows} == {"rules"}
    repo = SqliteRepository(db)
    assert repo.list_failure_analyses(RUN) == []  # scoring ran on a copy
    repo.close()


@pytest.mark.blackbox
def test_a_wrong_label_lowers_accuracy_and_shows_in_the_confusion_matrix(tmp_path: Path) -> None:
    db, truth = make_corpus(tmp_path)
    changed = {**truth, "F001": "environment"}  # the analyzer says locator
    rows = run_classification(db, RUN, write_labels(tmp_path / "labels.csv", changed))
    figures = {f.key: f for f in classification_figures(rows)}
    assert figures["classification_accuracy"].numerator == 43
    assert figures["classification_accuracy"].denominator == 44
    assert confusion(rows)[("environment", "locator")] == 1


@pytest.mark.blackbox
def test_blank_unknown_missing_and_too_few_labels_are_refused(tmp_path: Path) -> None:
    db, truth = make_corpus(tmp_path)
    labels = tmp_path / "labels.csv"
    with pytest.raises(ValidationError, match="no category yet"):
        run_classification(db, RUN, write_labels(labels, {**truth, "F002": ""}))
    with pytest.raises(ValidationError, match="not one of"):
        run_classification(db, RUN, write_labels(labels, {**truth, "F002": "flaky"}))
    partial = dict(list(truth.items())[:-2])
    with pytest.raises(ValidationError, match="differ"):
        run_classification(db, RUN, write_labels(labels, partial))
    (tmp_path / "few").mkdir()
    few_db, few_truth = make_corpus(tmp_path / "few", 30)
    with pytest.raises(ValidationError, match="at least 40"):
        run_classification(few_db, RUN, write_labels(labels, few_truth))


@pytest.mark.blackbox
def test_a_corpus_the_analyzer_has_already_seen_is_refused(tmp_path: Path) -> None:
    db, truth = make_corpus(tmp_path)
    repo = SqliteRepository(db)
    set_run_id(RUN)
    FailureAnalyzer(None, repo).analyze(RUN)  # the analyzer looks at the failures first
    repo.close()
    set_run_id("")
    with pytest.raises(ValidationError, match="already run"):
        run_classification(db, RUN, write_labels(tmp_path / "labels.csv", truth))


@pytest.mark.whitebox
def test_labels_file_needs_the_two_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("id,label\nF001,locator\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="columns"):
        read_labels(path)
    with pytest.raises(ValidationError, match="cannot read"):
        read_labels(tmp_path / "missing.csv")


def row(label: str, predicted: str, source: str = "rules") -> ClassificationRow:
    return ClassificationRow("F", label, predicted, label == predicted, source, 0.9, "CL", "rules")


@pytest.mark.blackbox
def test_precision_and_recall_are_worked_by_hand() -> None:
    rows = [
        row("locator", "locator"),
        row("locator", "locator"),
        row("locator", "unknown", "fallback"),
        row("environment", "locator"),
    ]
    by = {c: (n, p, r) for c, n, p, r in per_category(rows)}
    assert by["locator"] == (3, 2 / 3, 2 / 3)  # 2 of 3 predicted right, 2 of 3 labelled found
    assert by["environment"] == (1, None, 0.0)  # never predicted: precision undefined
    figures = {f.key: f for f in classification_figures(rows)}
    assert figures["classification_accuracy"].value == 2 / 4
    assert figures["rules_coverage"].value == 3 / 4


@pytest.mark.whitebox
def test_rows_survive_a_csv_round_trip_and_agreement_is_counted(tmp_path: Path) -> None:
    rows = [row("locator", "locator"), row("environment", "unknown", "fallback")]
    assert read_rows_csv(write_rows_csv(rows, tmp_path / "r.csv")) == rows
    assert agreement({"a": "x", "b": "y"}, {"a": "x", "b": "z"}) == 0.5
    assert agreement({}, {}) is None
