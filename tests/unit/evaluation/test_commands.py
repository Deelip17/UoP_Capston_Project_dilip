"""The ``aitaf evaluate`` commands (FR-35, FR-39).

``corpus`` needs Chromium and is tested in the integration suite; here the healing run,
the refusals and the classification path over a hand-built corpus are checked through
the real command line entry point.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from test_classify_eval import RUN, make_corpus, write_labels  # type: ignore[import-not-found]

from aitaf.cli import main
from aitaf.evaluation.corpus import LABELS_FILE


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("LLM_CALL_CAP", raising=False)


@pytest.mark.blackbox
def test_heal_writes_raw_rows_and_prints_the_figures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "healing.csv"
    assert main(["evaluate", "heal", "--count", "12", "--seed", "5", "--out", str(out)]) == 0
    text = capsys.readouterr().out
    assert "Healing success rate" in text and "False-heal rate" in text
    with out.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert sum(1 for r in rows if r["trial_type"] == "mutation") == 12
    assert sum(1 for r in rows if r["trial_type"] == "control") == 10


@pytest.mark.blackbox
def test_heal_with_the_model_step_runs_on_the_mock_provider(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "healing_llm.csv"
    assert main(["evaluate", "heal", "--count", "6", "--llm", "--out", str(out)]) == 0
    assert out.exists() and "Healing accuracy" in capsys.readouterr().out


@pytest.mark.blackbox
def test_a_count_outside_the_catalogue_fails_cleanly(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        main(["evaluate", "heal", "--count", "99", "--out", str(tmp_path / "x.csv")])


@pytest.mark.blackbox
def test_classify_without_a_corpus_says_what_to_do(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["evaluate", "classify", "--corpus", str(tmp_path / "none")]) == 1
    assert "evaluate corpus" in capsys.readouterr().err


@pytest.mark.blackbox
def test_classify_refuses_blank_labels_and_scores_filled_ones(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "corpus"
    folder.mkdir()
    db, truth = make_corpus(folder)
    assert db.name == "corpus.db" and RUN
    write_labels(folder / LABELS_FILE, {tc: "" for tc in truth})
    out = tmp_path / "scores.csv"
    args = ["evaluate", "classify", "--corpus", str(folder), "--out", str(out)]
    assert main(args) == 1
    assert "no category yet" in capsys.readouterr().err
    write_labels(folder / LABELS_FILE, truth)
    assert main(args) == 0
    text = capsys.readouterr().out
    assert "Classification accuracy" in text and "100.0% (44/44)" in text
    assert (tmp_path / "scores_rules.csv").exists()


@pytest.mark.blackbox
def test_classify_with_the_model_step_scores_both_configurations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "corpus"
    folder.mkdir()
    _, truth = make_corpus(folder)
    write_labels(folder / LABELS_FILE, truth)
    args = [
        "evaluate",
        "classify",
        "--corpus",
        str(folder),
        "--llm",
        "--out",
        str(tmp_path / "s.csv"),
    ]
    assert main(args) == 0
    text = capsys.readouterr().out
    assert "configuration rules:" in text and "configuration rules+model:" in text
