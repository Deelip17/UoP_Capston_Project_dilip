"""The Unit 6 metrics, computed from stored data (FR-39, FR-26, NFR-01, NFR-02).

Each metric carries a unit and a plain statement of what was counted, so a figure in a
report can be traced back to its data. A metric that cannot be computed (no data, no
labels, no source run) is ``None``, never zero. Numbers from the mock provider and from
a live model are never mixed without saying so: :func:`provider_label` reports which.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Mapping

from aitaf.core.models import MetricSample, ReviewStatus, TestResult
from aitaf.core.storage import Repository
from aitaf.reporting.model import MetricValue

GENERATION_COMPONENTS = frozenset(
    {"requirement_analyzer", "test_case_generator", "script_generator"}
)
LLM_COMPONENT = "llm_gateway"
RENDER_COMPONENT = "reporting_engine"


def percentile(values: Iterable[float], fraction: float) -> float | None:
    """Nearest-rank percentile; None for no data."""
    ordered = sorted(values)
    if not ordered:
        return None
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def provider_label(repo: Repository, run_ids: Iterable[str]) -> str:
    """``mock``, ``live``, ``mixed`` or ``none`` according to the audited LLM calls."""
    flags = {audit.mock for run_id in run_ids for audit in repo.list_audits(run_id)}
    if not flags:
        return "none"
    return "mixed" if len(flags) == 2 else ("mock" if flags == {True} else "live")


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _pass_rate(results: list[TestResult]) -> float | None:
    counted = [r for r in results if r.status != "skipped"]
    return _ratio(sum(1 for r in counted if r.status == "passed"), len(counted))


def _ran_as_designed(result: TestResult) -> bool:
    """A script ran as designed if it passed, or failed on an assertion.

    A missing locator (LookupError) or a runtime error means the script itself did not work
    on the page, so it is not counted as executable (same rule as the Unit 6 evaluation).
    """
    if result.status == "passed":
        return True
    return result.status == "failed" and result.error_type.rsplit(".", 1)[-1] == "AssertionError"


def _healing(repo: Repository, run_id: str) -> float | None:
    steps: dict[str, bool] = {}
    for event in repo.list_healing_events(run_id):
        steps[event.step_ref] = steps.get(event.step_ref, False) or event.outcome == "proposed"
    return _ratio(sum(steps.values()), len(steps))


def _accuracy(repo: Repository, run_id: str, labels: Mapping[str, str]) -> float | None:
    if not labels:
        return None
    predicted = {a.tc_id: a.category for a in repo.list_failure_analyses(run_id)}
    return _ratio(sum(1 for tc, label in labels.items() if predicted.get(tc) == label), len(labels))


def _samples(repo: Repository, run_ids: list[str]) -> list[MetricSample]:
    return [sample for run_id in run_ids for sample in repo.list_metrics(run_id)]


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def compute_metrics(
    repo: Repository,
    run_id: str,
    source_run_id: str | None,
    labels: Mapping[str, str] | None = None,
) -> list[MetricValue]:
    """All Unit 6 metrics for an execution run and the run that produced its scripts."""
    runs = [run_id]
    if source_run_id is not None and source_run_id != run_id:
        runs = [source_run_id, run_id]
    results = repo.list_results(run_id)
    samples = _samples(repo, runs)

    coverage: float | None = None
    executability: float | None = None
    if source_run_id is not None:
        requirements = {r.req_id for r in repo.list_requirements(source_run_id)}
        approved = {
            c.req_id
            for c in repo.list_test_cases(source_run_id, ReviewStatus.APPROVED)
            if c.req_id in requirements
        }
        coverage = _ratio(len(approved), len(requirements))
        scripts = {s.tc_id for s in repo.list_scripts(source_run_id)}
        ran = {r.tc_id for r in results if _ran_as_designed(r)}
        executability = _ratio(len(scripts & ran), len(scripts))

    generation = [
        s.duration_ms
        for s in samples
        if s.component in GENERATION_COMPONENTS and s.operation in ("analyze", "generate")
    ]
    llm = [s.duration_ms for s in samples if s.component == LLM_COMPONENT]
    non_llm = [s.duration_ms for s in samples if s.component == RENDER_COMPONENT]
    cost = sum(s.cost_usd for s in samples)

    return [
        MetricValue(
            "pass_rate",
            "Pass rate",
            _pass_rate(results),
            "ratio",
            "passed tests over executed tests (skipped tests excluded)",
        ),
        MetricValue(
            "requirement_coverage_ratio",
            "Requirement coverage",
            coverage,
            "ratio",
            "requirements with at least one approved test case over all requirements",
        ),
        MetricValue(
            "script_executability_rate",
            "Script executability",
            executability,
            "ratio",
            "scripts whose test passed or failed on an assertion (no missing element and no "
            "runtime error) over scripts generated",
        ),
        MetricValue(
            "healing_success_rate",
            "Healing repairs proposed",
            _healing(repo, run_id),
            "ratio",
            "steps with a proposed locator over steps that asked for healing "
            "(proposed, not verified)",
        ),
        MetricValue(
            "classification_accuracy",
            "Classification accuracy",
            _accuracy(repo, run_id, labels or {}),
            "ratio",
            "failures whose category equals the supplied label over labelled failures",
        ),
        MetricValue(
            "generation_latency_ms_median",
            "Generation latency (median)",
            _median(generation),
            "ms",
            "analyze and generate steps of the three generation components, LLM time included",
        ),
        MetricValue(
            "llm_latency_ms_median",
            "LLM call latency (median)",
            _median(llm),
            "ms",
            "gateway calls to the provider (mock or live, see the provider label)",
        ),
        MetricValue(
            "non_llm_latency_ms_p95",
            "Non-LLM latency (p95)",
            percentile(non_llm, 0.95),
            "ms",
            "report rendering samples, nearest-rank 95th percentile",
        ),
        MetricValue(
            "api_cost_usd",
            "API cost",
            cost,
            "usd",
            "sum of token costs of the runs involved (zero for the mock provider)",
        ),
        MetricValue(
            "api_cost_usd_per_run",
            "API cost per run",
            cost / len(runs),
            "usd",
            f"API cost divided by the {len(runs)} run(s) involved "
            "(the analysis run and the execution run when both exist)",
        ),
    ]
