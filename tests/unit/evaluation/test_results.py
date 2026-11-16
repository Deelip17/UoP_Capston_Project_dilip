"""Generation and latency figures, results table and charts (FR-39, NFR-01, objectives O2, O7).

Everything here uses hand-made rows, so each expected figure can be worked by hand.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.evaluation.classify_eval import ClassificationRow
from aitaf.evaluation.generation_eval import (
    GenerationTrial,
    read_generation_csv,
    write_generation_csv,
)
from aitaf.evaluation.healing_eval import HealingTrial
from aitaf.evaluation.latency_eval import (
    LatencySample,
    measure_report_latency,
    read_latency_csv,
    write_latency_csv,
)
from aitaf.evaluation.results import build_markdown, format_figure, write_charts, write_results
from aitaf.evaluation.summary import generation_figures, latency_figures


def trial(**kw: object) -> GenerationTrial:
    base: dict[str, object] = {
        "config": "sg-v2 mock",
        "provider": "mock",
        "page_context": True,
        "cases": 54,
        "scripts": 50,
        "rejected": 4,
        "locators": 12,
        "valid_locators": 12,
        "passed": 20,
        "failed": 30,
        "errors": 0,
        "executable": 25,
        "llm_calls": 92,
        "tokens_in": 1000,
        "tokens_out": 500,
        "cost_usd": 0.0123,
        "generation_s": 5.0,
        "script_step_s": 2.0,
    }
    base.update(kw)
    return GenerationTrial(**base)  # type: ignore[arg-type]


def healing(kind: str = "id", ok: bool = True) -> HealingTrial:
    return HealingTrial("H", "mutation", "M-x", "x", kind, "id", ok, ok, "id=y", 0.9, 1.0, "")


@pytest.mark.blackbox
def test_generation_figures_are_worked_by_hand() -> None:
    by = {f.key: f for f in generation_figures(trial())}
    assert by["script_executability"].value == 25 / 50
    assert by["script_pass_rate"].value == 20 / 50
    assert by["locator_validity"].value == 1.0
    assert by["scripts_accepted"].value == 50 / 54
    assert by["api_cost_usd"].value == 0.0123


@pytest.mark.whitebox
def test_no_scripts_gives_none_not_zero() -> None:
    by = {f.key: f for f in generation_figures(trial(scripts=0, locators=0, valid_locators=0))}
    assert by["script_executability"].value is None
    assert by["locator_validity"].value is None


@pytest.mark.blackbox
def test_generation_rows_round_trip(tmp_path: Path) -> None:
    rows = [trial(), trial(config="sg-v1 live", provider="live", page_context=False)]
    assert read_generation_csv(write_generation_csv(rows, tmp_path / "g.csv")) == rows


@pytest.mark.blackbox
def test_latency_excludes_the_warm_up_sample(tmp_path: Path) -> None:
    rows = [LatencySample(1, "op", 900.0, True)] + [
        LatencySample(n, "op", float(n * 10), False) for n in range(2, 7)
    ]
    assert read_latency_csv(write_latency_csv(rows, tmp_path / "l.csv")) == rows
    by = {f.key: f for f in latency_figures(rows)}
    assert by["non_llm_latency_ms_median"].value == 40.0  # 20, 30, 40, 50, 60
    assert by["non_llm_latency_ms_p95"].value == 60.0
    assert by["non_llm_latency_ms_median"].denominator == 5


@pytest.mark.whitebox
def test_latency_needs_two_samples_and_results() -> None:
    with pytest.raises(ValueError):
        measure_report_latency("unused.db", 1)


@pytest.mark.whitebox
def test_figures_print_with_their_counts() -> None:
    by = {f.key: f for f in generation_figures(trial())}
    assert format_figure(by["script_executability"]) == "50.0% (25/50)"
    assert format_figure(by["api_cost_usd"]) == "$0.0123"
    assert format_figure(generation_figures(trial(scripts=0))[0]) == "n/a"


def classification_rows() -> list[ClassificationRow]:
    return [
        ClassificationRow("F1", "locator", "locator", True, "rules", 0.9, "CL", "rules"),
        ClassificationRow(
            "F2", "test_data", "assertion_defect", False, "rules", 0.9, "CL", "rules"
        ),
    ]


@pytest.mark.blackbox
def test_markdown_reports_every_section_and_the_limits() -> None:
    text = build_markdown(
        [healing(), healing("text", False)],
        {"rules": classification_rows()},
        [trial(), trial(config="sg-v1 mock", page_context=False, executable=0)],
        [LatencySample(1, "op", 9.0, True), LatencySample(2, "op", 5.0, False)],
    )
    for heading in ("## Healing", "## Failure classification", "## Script generation", "## Limits"):
        assert heading in text
    assert "test_data to assertion_defect: 1" in text
    assert "sg-v1 mock" in text and "provider: mock" in text
    assert "50.0% (1/2)" in text  # healing success: one of two


@pytest.mark.blackbox
def test_charts_are_written_as_png(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    paths = write_charts(
        tmp_path,
        [healing("id"), healing("text", False)],
        classification_rows(),
        [trial(), trial(config="sg-v1 mock", executable=0, valid_locators=0)],
    )
    assert [p.name for p in paths] == [
        "healing_by_kind.png",
        "classification.png",
        "generation.png",
    ]
    assert all(p.read_bytes().startswith(b"\x89PNG") for p in paths)


@pytest.mark.blackbox
def test_results_files_are_written_from_the_raw_csv_files(tmp_path: Path) -> None:
    from aitaf.evaluation.classify_eval import write_rows_csv
    from aitaf.evaluation.healing_eval import write_trials_csv

    write_trials_csv([healing(), healing("text", False)], tmp_path / "healing.csv")
    write_rows_csv(classification_rows(), tmp_path / "classification_rules.csv")
    write_generation_csv([trial()], tmp_path / "generation.csv")
    write_latency_csv(
        [LatencySample(1, "op", 9.0, True), LatencySample(2, "op", 5.0, False)],
        tmp_path / "latency.csv",
    )
    written = write_results(tmp_path, charts=False)
    assert [p.name for p in written] == ["RESULTS.md"]
    assert "Evaluation results" in (tmp_path / "RESULTS.md").read_text(encoding="utf-8")
