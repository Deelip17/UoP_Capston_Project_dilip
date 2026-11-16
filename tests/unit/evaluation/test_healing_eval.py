"""Healing evaluation over the seeded mutations (FR-24, FR-26, FR-38, NFR-03).

The harness must be reproducible (same seed, same mutations), must keep the ground truth away
from the healer, and must compute every figure from the raw rows alone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.evaluation import (
    HealingTrial,
    read_trials_csv,
    run_healing_evaluation,
    select_mutations,
    write_trials_csv,
)
from aitaf.evaluation.summary import healing_by_kind, healing_figures, percentile
from aitaf.sampleapp import CATALOGUE, render_page


def trial(
    kind: str = "mutation",
    healed: bool = True,
    correct: bool = True,
    mutation_kind: str = "id",
    ms: float = 1.0,
) -> HealingTrial:
    return HealingTrial(
        "H-1", kind, "M-x", "x", mutation_kind, "id", healed, correct, "", 0.9, ms, ""
    )


@pytest.fixture(scope="module")
def trials() -> list[HealingTrial]:
    return run_healing_evaluation(seed=42)


@pytest.mark.blackbox
def test_the_same_seed_selects_the_same_mutations_and_another_seed_differs() -> None:
    first = select_mutations(7, 30)
    assert first == select_mutations(7, 30)
    assert first != select_mutations(8, 30)
    assert len(first) == 30 and len(set(first)) == 30
    assert all(m in CATALOGUE for m in first)


@pytest.mark.blackbox
def test_count_outside_the_catalogue_is_refused() -> None:
    for bad in (0, len(CATALOGUE) + 1):
        with pytest.raises(ValueError):
            select_mutations(1, bad)


@pytest.mark.blackbox
def test_the_evaluation_covers_at_least_thirty_mutations_and_every_element_as_a_control(
    trials: list[HealingTrial],
) -> None:
    mutations = [t for t in trials if t.trial_type == "mutation"]
    controls = [t for t in trials if t.trial_type == "control"]
    assert len(mutations) >= 30
    assert len(controls) == 10
    assert {t.mutation_kind for t in mutations} == {"id", "class", "xpath", "text"}


@pytest.mark.blackbox
def test_a_correct_repair_points_at_the_element_the_mutation_touched(
    trials: list[HealingTrial],
) -> None:
    login = next(t for t in trials if t.mutation_id == "M-login_submit-id")
    assert login.healed and login.correct and login.proposed
    for t in (t for t in trials if t.trial_type == "mutation"):
        assert not t.correct or t.healed  # nothing is correct without a proposal


@pytest.mark.blackbox
def test_a_control_is_correct_only_when_nothing_is_proposed(trials: list[HealingTrial]) -> None:
    for t in (t for t in trials if t.trial_type == "control"):
        assert t.correct is (not t.healed)


@pytest.mark.whitebox
def test_the_healer_never_sees_the_ground_truth_attribute() -> None:
    assert "data-gt" not in render_page("login", ["M-login_submit-id"])
    assert "data-gt" in render_page("login", ["M-login_submit-id"], oracle=True)


@pytest.mark.blackbox
def test_results_are_the_same_on_every_run_apart_from_timing() -> None:
    def key(rows: list[HealingTrial]) -> list[tuple[str, bool, bool, str]]:
        return [(t.trial_id, t.healed, t.correct, t.proposed) for t in rows]

    assert key(run_healing_evaluation(seed=3, count=12)) == key(
        run_healing_evaluation(seed=3, count=12)
    )


@pytest.mark.blackbox
def test_csv_round_trip_keeps_every_row(tmp_path: Path, trials: list[HealingTrial]) -> None:
    path = write_trials_csv(trials, tmp_path / "out" / "healing.csv")
    assert read_trials_csv(path) == trials
    assert path.read_text(encoding="utf-8").splitlines()[0].startswith("trial_id,trial_type")


@pytest.mark.blackbox
def test_figures_are_worked_by_hand_from_known_rows() -> None:
    rows = [
        trial(),  # healed, correct
        trial(),  # healed, correct
        trial(correct=False),  # healed the wrong element
        trial(healed=False, correct=False),  # not healed
        trial("control", healed=False, correct=True),
        trial("control", healed=True, correct=False),  # proposed where the element is absent
    ]
    by = {f.key: f for f in healing_figures(rows)}
    assert (by["healing_success_rate"].numerator, by["healing_success_rate"].denominator) == (3, 4)
    assert by["healing_accuracy"].value == 2 / 4
    assert by["healing_precision"].value == 2 / 3
    assert by["false_heal_rate"].value == 2 / 6  # one wrong element + one control heal
    assert by["control_rejection_rate"].value == 1 / 2


@pytest.mark.whitebox
def test_a_ratio_with_no_cases_is_none_not_zero() -> None:
    by = {f.key: f for f in healing_figures([])}
    assert by["healing_success_rate"].value is None
    assert by["healing_time_ms_median"].value is None
    assert percentile([], 0.95) is None


@pytest.mark.whitebox
def test_percentile_is_nearest_rank() -> None:
    assert percentile([5, 1, 3, 2, 4], 0.95) == 5
    assert percentile([5, 1, 3, 2, 4], 0.5) == 3


@pytest.mark.blackbox
def test_breakdown_by_mutation_kind() -> None:
    rows = [
        trial(mutation_kind="id"),
        trial(mutation_kind="id", healed=False, correct=False),
        trial(mutation_kind="text"),
        trial("control", mutation_kind="absent"),
    ]
    assert healing_by_kind(rows) == [("id", 2, 1, 1), ("text", 1, 1, 1)]
