"""Figures computed from the raw evaluation rows (FR-39, NFR-01, NFR-03).

Every function takes the rows exactly as they are stored in the CSV files and returns
plain numbers with the counts they came from, so a reader can recompute each figure by
hand from the raw file. A ratio with no cases is None, never zero.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from aitaf.evaluation.healing_eval import HealingTrial


@dataclass(frozen=True)
class Figure:
    """One reported figure: a value, its unit and the counts behind it."""

    key: str
    label: str
    value: float | None
    unit: str  # ratio, ms, usd, count
    numerator: int | None = None
    denominator: int | None = None
    basis: str = ""


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def percentile(values: Iterable[float], fraction: float) -> float | None:
    """Nearest-rank percentile; None for no data."""
    ordered = sorted(values)
    if not ordered:
        return None
    return ordered[max(1, math.ceil(fraction * len(ordered))) - 1]


def median(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None


def ratio_figure(key: str, label: str, numerator: int, denominator: int, basis: str) -> Figure:
    return Figure(key, label, ratio(numerator, denominator), "ratio", numerator, denominator, basis)


def healing_figures(trials: Sequence[HealingTrial]) -> list[Figure]:
    """Healing success, correctness, false-heal rate and decision time."""
    positives = [t for t in trials if t.trial_type == "mutation"]
    controls = [t for t in trials if t.trial_type == "control"]
    healed = [t for t in positives if t.healed]
    wrong = [t for t in healed if not t.correct]
    false_heals = len(wrong) + sum(1 for t in controls if t.healed)
    times = [t.elapsed_ms for t in trials]
    return [
        ratio_figure(
            "healing_success_rate",
            "Healing success rate",
            len(healed),
            len(positives),
            "mutated locators for which a repair was proposed, over mutated locators",
        ),
        ratio_figure(
            "healing_accuracy",
            "Healing accuracy",
            sum(1 for t in positives if t.correct),
            len(positives),
            "repairs that point at the right element (checked against the hidden ground truth), "
            "over mutated locators",
        ),
        ratio_figure(
            "healing_precision",
            "Healing precision",
            len(healed) - len(wrong),
            len(healed),
            "proposed repairs that point at the right element, over proposed repairs",
        ),
        ratio_figure(
            "false_heal_rate",
            "False-heal rate",
            false_heals,
            len(positives) + len(controls),
            "repairs of the wrong element, plus repairs proposed where the element is absent, "
            "over all trials",
        ),
        ratio_figure(
            "control_rejection_rate",
            "Control rejection rate",
            sum(1 for t in controls if not t.healed),
            len(controls),
            "absent-element trials where no repair was proposed, over absent-element trials",
        ),
        Figure(
            "healing_time_ms_median",
            "Healing decision time (median)",
            median(times),
            "ms",
            None,
            len(times),
            "time of one healing request (similarity rungs only; no browser)",
        ),
        Figure(
            "healing_time_ms_p95",
            "Healing decision time (p95)",
            percentile(times, 0.95),
            "ms",
            None,
            len(times),
            "nearest-rank 95th percentile of the same samples",
        ),
    ]


def healing_by_kind(trials: Sequence[HealingTrial]) -> list[tuple[str, int, int, int]]:
    """(mutation kind, trials, repaired, repaired correctly) for the mutation trials."""
    groups: dict[str, list[HealingTrial]] = defaultdict(list)
    for trial in trials:
        if trial.trial_type == "mutation":
            groups[trial.mutation_kind].append(trial)
    return [
        (kind, len(rows), sum(t.healed for t in rows), sum(t.correct for t in rows))
        for kind, rows in sorted(groups.items())
    ]
