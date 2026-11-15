"""Unit 6 metrics computed from stored data (FR-39, FR-26, NFR-01, NFR-02).

Every expected value is worked out by hand from the seeded records in
``pipeline_records.seeded_repo``. Each metric states its basis, so a number in a
report can be traced to what was counted; a metric that cannot be computed is None,
never zero.
"""

from __future__ import annotations

import pytest
from pipeline_records import EXEC, SOURCE, audit, seeded_repo

from aitaf.core.storage import InMemoryRepository
from aitaf.reporting.metrics import compute_metrics, percentile, provider_label


def values(**kwargs: object) -> dict[str, float | None]:
    repo = seeded_repo()
    found = compute_metrics(repo, EXEC, SOURCE, **kwargs)  # type: ignore[arg-type]
    return {m.key: m.value for m in found}


@pytest.mark.blackbox
def test_pass_rate_ignores_skipped_tests() -> None:
    assert values()["pass_rate"] == pytest.approx(1 / 3)


@pytest.mark.blackbox
def test_requirement_coverage_counts_requirements_with_an_approved_case() -> None:
    """O1: R1 and R2 have an approved case; R3 only a pending one; R4 none."""
    assert values()["requirement_coverage_ratio"] == 0.5


@pytest.mark.blackbox
def test_script_executability_counts_scripts_that_ran_without_error() -> None:
    """O2: TC-1 passed and TC-2 failed (both ran); TC-3 errored; TC-4 never ran."""
    assert values()["script_executability_rate"] == 0.5


@pytest.mark.blackbox
def test_healing_success_rate_is_healed_steps_over_healing_requests() -> None:
    """Two steps asked for healing; one of them got a proposed locator."""
    assert values()["healing_success_rate"] == 0.5


@pytest.mark.blackbox
def test_classification_accuracy_is_measured_against_the_supplied_labels() -> None:
    labels = {"TC-2": "locator", "TC-3": "environment"}
    assert values(labels=labels)["classification_accuracy"] == 0.5
    assert values()["classification_accuracy"] is None


@pytest.mark.whitebox
def test_a_labelled_failure_without_an_analysis_counts_as_not_classified() -> None:
    labels = {"TC-2": "locator", "TC-9": "environment"}
    assert values(labels=labels)["classification_accuracy"] == 0.5


@pytest.mark.blackbox
def test_latencies_are_split_into_generation_llm_and_non_llm() -> None:
    found = values()
    assert found["generation_latency_ms_median"] == 200.0
    assert found["llm_latency_ms_median"] == 90.0
    assert found["non_llm_latency_ms_p95"] == 50.0


@pytest.mark.blackbox
def test_api_cost_is_summed_over_both_runs_and_per_run() -> None:
    found = values()
    assert found["api_cost_usd"] == pytest.approx(0.0055)
    assert found["api_cost_usd_per_run"] == pytest.approx(0.00275)


@pytest.mark.blackbox
def test_every_metric_states_its_unit_and_its_basis_and_keys_are_unique() -> None:
    found = compute_metrics(seeded_repo(), EXEC, SOURCE)
    assert len({m.key for m in found}) == len(found)
    for metric in found:
        assert metric.label and metric.unit and metric.basis
    assert {"pass_rate", "requirement_coverage_ratio", "api_cost_usd"} <= {m.key for m in found}


@pytest.mark.whitebox
def test_without_a_source_run_the_pipeline_metrics_cannot_be_computed() -> None:
    found = {m.key: m.value for m in compute_metrics(seeded_repo(), EXEC, None)}
    assert found["requirement_coverage_ratio"] is None
    assert found["script_executability_rate"] is None
    assert found["pass_rate"] == pytest.approx(1 / 3)


@pytest.mark.whitebox
def test_a_run_with_no_data_gives_none_not_zero() -> None:
    repo = InMemoryRepository()
    from pipeline_records import run

    repo.create_run(run("empty"))
    found = {m.key: m.value for m in compute_metrics(repo, "empty", None)}
    assert all(
        found[key] is None
        for key in (
            "pass_rate",
            "healing_success_rate",
            "generation_latency_ms_median",
            "llm_latency_ms_median",
            "non_llm_latency_ms_p95",
        )
    )
    assert found["api_cost_usd"] == 0.0


@pytest.mark.whitebox
@pytest.mark.parametrize(
    ("data", "fraction", "expected"),
    [
        ([10.0], 0.95, 10.0),
        ([10.0, 20.0, 30.0, 40.0, 50.0], 0.95, 50.0),
        ([1.0, 2.0, 3.0, 4.0], 0.5, 2.0),
    ],
)
def test_percentile_uses_the_nearest_rank(
    data: list[float], fraction: float, expected: float
) -> None:
    assert percentile(data, fraction) == expected


@pytest.mark.whitebox
def test_percentile_of_nothing_is_none() -> None:
    assert percentile([], 0.95) is None


@pytest.mark.blackbox
def test_the_provider_label_says_whether_numbers_came_from_mock_or_live_calls() -> None:
    assert provider_label(seeded_repo(), [SOURCE, EXEC]) == "mock"
    assert provider_label(seeded_repo(live=True), [SOURCE, EXEC]) == "live"
    mixed = seeded_repo()
    mixed.add_audit(audit("c9", EXEC, mock=False))
    assert provider_label(mixed, [SOURCE, EXEC]) == "mixed"
    empty = InMemoryRepository()
    from pipeline_records import run

    empty.create_run(run("r"))
    assert provider_label(empty, ["r"]) == "none"
