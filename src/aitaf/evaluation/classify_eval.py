"""Score the Failure Analyzer against the author's own labels (FR-27, FR-28, NFR-15, objective O4).

The labels are read first and checked: every failed test of the corpus run needs one of
the six categories, there must be at least forty, and the analyzer must not have seen the
run before (a corpus whose failures were already analysed is refused, so the labels cannot
have been influenced by the analyzer's answers). The analyzer then runs on a throw-away copy
of the corpus database, once with rules only and, if a gateway is given, once with the model
step as well; each configuration is scored separately and the mock and live models are never
mixed. The labels file's SHA-256 is recorded so the labelled set is traceable.
"""

from __future__ import annotations

import csv
import hashlib
import tempfile
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

from aitaf.core.errors import ValidationError
from aitaf.core.llm import LlmGateway
from aitaf.core.logging import set_run_id
from aitaf.core.models import FailureCategory
from aitaf.core.storage import Repository, SqliteRepository
from aitaf.diagnosis import FailureAnalyzer
from aitaf.evaluation.corpus import MIN_FAILURES, copy_corpus
from aitaf.evaluation.summary import Figure, ratio, ratio_figure

CATEGORIES: tuple[str, ...] = get_args(FailureCategory)


@dataclass(frozen=True)
class ClassificationRow:
    """One failure: the author's label, the analyzer's answer and how it was reached."""

    tc_id: str
    label: str
    predicted: str
    correct: bool
    source: str
    confidence: float
    cluster_id: str
    config: str


COLUMNS = (
    "tc_id",
    "label",
    "predicted",
    "correct",
    "source",
    "confidence",
    "cluster_id",
    "config",
)


def read_labels(path: Path | str) -> dict[str, str]:
    """Labels from a CSV with the columns tc_id and category; every row must be filled in."""
    try:
        with Path(path).open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {"tc_id", "category"} <= set(reader.fieldnames):
                raise ValidationError("the labels file needs the columns tc_id and category")
            labels: dict[str, str] = {}
            for row in reader:
                tc_id = (row.get("tc_id") or "").strip()
                category = (row.get("category") or "").strip()
                if not category:
                    raise ValidationError(f"{tc_id}: no category yet; label every failure first")
                if category not in CATEGORIES:
                    raise ValidationError(
                        f"{tc_id}: {category!r} is not one of {', '.join(CATEGORIES)}"
                    )
                labels[tc_id] = category
    except OSError as exc:
        raise ValidationError(f"cannot read the labels file: {exc.strerror}") from exc
    return labels


def labels_digest(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_classification(
    corpus_db: Path | str,
    run_id: str,
    labels_path: Path | str,
    *,
    gateway_factory: Callable[[Repository], LlmGateway] | None = None,
    config: str = "rules",
    evidence_dir: Path | str | None = None,
) -> list[ClassificationRow]:
    """Score one analyzer configuration; ``config`` names it in the rows."""
    labels = read_labels(labels_path)
    if len(labels) < MIN_FAILURES:
        raise ValidationError(f"at least {MIN_FAILURES} labelled failures are needed")
    with tempfile.TemporaryDirectory() as work:
        copy = copy_corpus(corpus_db, Path(work) / "scored.db")
        repo = SqliteRepository(copy)
        try:
            if repo.list_failure_analyses(run_id):
                raise ValidationError(
                    "the analyzer has already run on this corpus, so the labels cannot be "
                    "called independent; build a new corpus and label it first"
                )
            failed = {r.tc_id for r in repo.list_results(run_id) if r.status in ("failed", "error")}
            if failed != set(labels):
                missing = sorted(failed - set(labels))
                extra = sorted(set(labels) - failed)
                raise ValidationError(
                    f"labels and failures differ (unlabelled: {missing[:5]}, unknown: {extra[:5]})"
                )
            set_run_id(run_id)
            analyzer = FailureAnalyzer(
                gateway_factory(repo) if gateway_factory else None,
                repo,
                evidence_dir=Path(evidence_dir) if evidence_dir else None,
            )
            outcome = analyzer.analyze(run_id)
        finally:
            repo.close()
            set_run_id("")
    return [
        ClassificationRow(
            tc_id=a.tc_id,
            label=labels[a.tc_id],
            predicted=a.category,
            correct=a.category == labels[a.tc_id],
            source=a.source,
            confidence=round(a.confidence, 4),
            cluster_id=a.cluster_id,
            config=config,
        )
        for a in sorted(outcome.analyses, key=lambda a: a.tc_id)
    ]


def write_rows_csv(rows: Sequence[ClassificationRow], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(COLUMNS)
        for r in rows:
            writer.writerow(
                [r.tc_id, r.label, r.predicted, r.correct, r.source, r.confidence, r.cluster_id]
                + [r.config]
            )
    return target


def read_rows_csv(path: Path | str) -> list[ClassificationRow]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return [
            ClassificationRow(
                row["tc_id"],
                row["label"],
                row["predicted"],
                row["correct"] == "True",
                row["source"],
                float(row["confidence"]),
                row["cluster_id"],
                row["config"],
            )
            for row in csv.DictReader(handle)
        ]


def confusion(rows: Sequence[ClassificationRow]) -> dict[tuple[str, str], int]:
    """Counts keyed by (label, predicted)."""
    return dict(Counter((r.label, r.predicted) for r in rows))


def per_category(
    rows: Sequence[ClassificationRow],
) -> list[tuple[str, int, float | None, float | None]]:
    """(category, labelled count, precision, recall) for every category that occurs."""
    out = []
    for category in CATEGORIES:
        labelled = sum(1 for r in rows if r.label == category)
        predicted = sum(1 for r in rows if r.predicted == category)
        hits = sum(1 for r in rows if r.label == category and r.predicted == category)
        if labelled or predicted:
            out.append((category, labelled, ratio(hits, predicted), ratio(hits, labelled)))
    return out


def classification_figures(rows: Sequence[ClassificationRow]) -> list[Figure]:
    """Accuracy overall and by how the answer was reached."""
    by_rules = [r for r in rows if r.source == "rules"]
    return [
        ratio_figure(
            "classification_accuracy",
            "Classification accuracy",
            sum(r.correct for r in rows),
            len(rows),
            "failures whose category equals the author's label, over labelled failures",
        ),
        ratio_figure(
            "rules_coverage",
            "Failures decided by the rules",
            len(by_rules),
            len(rows),
            "failures classified by a deterministic rule, over all failures",
        ),
        ratio_figure(
            "rules_accuracy",
            "Accuracy of the rule-decided failures",
            sum(r.correct for r in by_rules),
            len(by_rules),
            "rule-decided failures that match the label, over rule-decided failures",
        ),
    ]


def agreement(labels: Mapping[str, str], other: Mapping[str, str]) -> float | None:
    """Share of failures on which two labellings agree (for a second labeller)."""
    shared = set(labels) & set(other)
    return ratio(sum(1 for t in shared if labels[t] == other[t]), len(shared))
