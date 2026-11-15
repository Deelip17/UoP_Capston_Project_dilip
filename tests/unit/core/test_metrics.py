"""Metrics hooks: timers, outcome counters, token and cost logging.

Requirements: NFR-35 (metrics hooks exist in the core), NFR-34 (run identifier),
FR-33 (API cost per run and generation latency come from stored data).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError as PydanticValidationError

from aitaf.core.errors import PolicyError
from aitaf.core.logging import set_run_id
from aitaf.core.metrics import Metrics, run_cost, summarise, timed, token_cost
from aitaf.core.models import MetricSample, Run, RunStatus
from aitaf.core.storage import InMemoryRepository

NOW = datetime(2026, 11, 14, tzinfo=UTC)


class FakeClock:
    def __init__(self, step: float = 0.25) -> None:
        self._now = 100.0
        self._step = step

    def __call__(self) -> float:
        self._now += self._step
        return self._now


@pytest.fixture
def repo() -> Iterator[InMemoryRepository]:
    repository = InMemoryRepository()
    repository.create_run(
        Run(
            run_id="run-1",
            started_at=NOW,
            status=RunStatus.RUNNING,
            provider="mock",
            environment="t",
        )
    )
    set_run_id("run-1")
    yield repository
    set_run_id("")


def sample(
    component: str, operation: str, ms: float, outcome: str = "ok", **extra: float
) -> MetricSample:
    return MetricSample(
        run_id="run-1",
        component=component,
        operation=operation,
        outcome=outcome,  # type: ignore[arg-type]
        duration_ms=ms,
        created_at=NOW,
        **extra,  # type: ignore[arg-type]
    )


@pytest.mark.blackbox
def test_a_timed_block_records_latency_and_an_ok_outcome(repo: InMemoryRepository) -> None:
    metrics = Metrics(repo, clock=FakeClock(0.25))
    with metrics.time("requirement_analyzer", "analyze") as probe:
        probe.detail = "7 requirements"
    (stored,) = repo.list_metrics("run-1")
    assert (stored.component, stored.operation, stored.outcome) == (
        "requirement_analyzer",
        "analyze",
        "ok",
    )
    assert stored.duration_ms == pytest.approx(250.0)
    assert stored.detail == "7 requirements"


@pytest.mark.blackbox
def test_a_failing_block_is_recorded_as_error_and_the_exception_still_propagates(
    repo: InMemoryRepository,
) -> None:
    metrics = Metrics(repo)
    with pytest.raises(ValueError, match="boom"), metrics.time("test_case_generator", "generate"):
        raise ValueError("boom")
    (stored,) = repo.list_metrics("run-1")
    assert stored.outcome == "error"


@pytest.mark.blackbox
def test_tokens_and_cost_are_logged_with_the_sample(repo: InMemoryRepository) -> None:
    with Metrics(repo).time("llm_gateway", "requirement_analyzer") as probe:
        probe.tokens_in, probe.tokens_out, probe.cost_usd = 120, 30, 0.0021
    (stored,) = repo.list_metrics("run-1")
    assert (stored.tokens_in, stored.tokens_out, stored.cost_usd) == (120, 30, 0.0021)


@pytest.mark.blackbox
def test_samples_need_an_active_run(repo: InMemoryRepository) -> None:
    set_run_id("")
    with pytest.raises(PolicyError), Metrics(repo).time("x", "y"):
        pass


@pytest.mark.blackbox
def test_no_metrics_object_means_no_overhead_and_no_error() -> None:
    with timed(None, "requirement_analyzer", "analyze") as probe:
        probe.tokens_in = 5
    assert probe.tokens_in == 5


@pytest.mark.blackbox
def test_timed_delegates_to_the_recorder_when_present(repo: InMemoryRepository) -> None:
    with timed(Metrics(repo), "self_healing", "heal"):
        pass
    assert [s.component for s in repo.list_metrics("run-1")] == ["self_healing"]


@pytest.mark.blackbox
@pytest.mark.parametrize(
    ("tokens_in", "tokens_out", "price_in", "price_out", "expected"),
    [
        (1000, 500, 0.5, 1.5, 1.25),
        (1000, 500, 0.0, 0.0, 0.0),
        (0, 0, 9.0, 9.0, 0.0),
        (250, 0, 2.0, 0.0, 0.5),
    ],
)
def test_token_cost(
    tokens_in: int, tokens_out: int, price_in: float, price_out: float, expected: float
) -> None:
    assert token_cost(tokens_in, tokens_out, price_in, price_out) == pytest.approx(expected)


@pytest.mark.blackbox
def test_summary_groups_by_component_and_operation() -> None:
    samples = [
        sample(
            "llm_gateway", "requirement_analyzer", 10.0, tokens_in=100, tokens_out=20, cost_usd=0.01
        ),
        sample(
            "llm_gateway", "requirement_analyzer", 30.0, tokens_in=50, tokens_out=10, cost_usd=0.02
        ),
        sample("llm_gateway", "requirement_analyzer", 20.0, outcome="error"),
        sample("requirement_analyzer", "analyze", 80.0),
    ]
    rows = summarise(samples)
    assert [(r.component, r.operation) for r in rows] == [
        ("llm_gateway", "requirement_analyzer"),
        ("requirement_analyzer", "analyze"),
    ]
    gateway = rows[0]
    assert (gateway.count, gateway.errors) == (3, 1)
    assert gateway.median_ms == pytest.approx(20.0)
    assert gateway.total_ms == pytest.approx(60.0)
    assert (gateway.tokens_in, gateway.tokens_out) == (150, 30)
    assert gateway.cost_usd == pytest.approx(0.03)


@pytest.mark.whitebox
def test_run_cost_sums_every_sample() -> None:
    assert (
        run_cost([sample("a", "b", 1.0, cost_usd=0.5), sample("a", "b", 1.0, cost_usd=0.25)])
        == 0.75
    )
    assert run_cost([]) == 0.0


@pytest.mark.whitebox
def test_summary_of_nothing_is_empty() -> None:
    assert summarise([]) == []


@pytest.mark.whitebox
def test_the_median_of_an_even_count_is_the_mean_of_the_middle_pair() -> None:
    rows = summarise([sample("a", "b", ms) for ms in (10.0, 20.0, 30.0, 100.0)])
    assert rows[0].median_ms == pytest.approx(25.0)


@pytest.mark.whitebox
@pytest.mark.parametrize("bad", [{"duration_ms": -1.0}, {"tokens_in": -1}, {"cost_usd": -0.1}])
def test_a_sample_rejects_negative_values(bad: dict[str, float]) -> None:
    fields: dict[str, object] = {
        "run_id": "r",
        "component": "c",
        "operation": "o",
        "outcome": "ok",
        "duration_ms": 1.0,
        "created_at": NOW,
    }
    fields.update(bad)
    with pytest.raises(PydanticValidationError):
        MetricSample(**fields)  # type: ignore[arg-type]
