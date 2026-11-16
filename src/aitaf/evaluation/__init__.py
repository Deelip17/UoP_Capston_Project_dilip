"""Evaluation harness (FR-38, FR-39, NFR-01, NFR-03): measures the framework against ground truth.

The package runs the components against the sample shop and writes raw CSV files that
every reported figure can be recomputed from. It may import any component (it is a
tool, like the command line); the real work stays in the components.
"""

from aitaf.evaluation.healing_eval import (
    HealingTrial,
    read_trials_csv,
    run_healing_evaluation,
    select_mutations,
    write_trials_csv,
)

__all__ = [
    "HealingTrial",
    "read_trials_csv",
    "run_healing_evaluation",
    "select_mutations",
    "write_trials_csv",
]
