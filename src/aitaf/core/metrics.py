"""Metrics hooks: timers, outcome counters, token and cost logging (NFR-35).

Every instrumented operation writes one :class:`~aitaf.core.models.MetricSample`
to persistence under the current run ID: component, operation, outcome, latency,
tokens and cost. Unit 6 (latency, cost, healing overhead) and the Dashboard read
these rows, so nothing has to be reconstructed later. Instrumentation is optional:
components accept ``metrics=None`` and then pay no cost.
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime

from aitaf.core.errors import PolicyError
from aitaf.core.logging import current_run_id
from aitaf.core.models import MetricSample
from aitaf.core.storage import Repository


@dataclass
class Probe:
    """Values a timed block can set before it ends."""

    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    detail: str = ""


@dataclass(frozen=True)
class MetricSummary:
    """Aggregate of the samples of one component operation."""

    component: str
    operation: str
    count: int
    errors: int
    median_ms: float
    total_ms: float
    tokens_in: int
    tokens_out: int
    cost_usd: float


def token_cost(
    tokens_in: int, tokens_out: int, price_in_per_1k: float, price_out_per_1k: float
) -> float:
    """Cost of a call from token counts and the configured prices per 1,000 tokens."""
    return tokens_in / 1000 * price_in_per_1k + tokens_out / 1000 * price_out_per_1k


class Metrics:
    """Writes metric samples for the current run."""

    def __init__(self, repo: Repository, clock: Callable[[], float] = time.perf_counter) -> None:
        self._repo = repo
        self._clock = clock

    def record(
        self, component: str, operation: str, outcome: str, duration_ms: float, probe: Probe
    ) -> None:
        run_id = current_run_id()
        if not run_id:
            raise PolicyError("no run ID is set; start a run before recording metrics")
        self._repo.add_metric(
            run_id,
            MetricSample(
                run_id=run_id,
                component=component,
                operation=operation,
                outcome="ok" if outcome == "ok" else "error",
                detail=probe.detail,
                duration_ms=duration_ms,
                tokens_in=probe.tokens_in,
                tokens_out=probe.tokens_out,
                cost_usd=probe.cost_usd,
                created_at=datetime.now(UTC),
            ),
        )

    @contextmanager
    def time(self, component: str, operation: str) -> Iterator[Probe]:
        """Time a block; an exception is recorded as an error outcome and re-raised."""
        probe = Probe()
        started = self._clock()
        outcome = "ok"
        try:
            yield probe
        except Exception:
            outcome = "error"
            raise
        finally:
            self.record(component, operation, outcome, (self._clock() - started) * 1000, probe)


def timed(metrics: Metrics | None, component: str, operation: str) -> AbstractContextManager[Probe]:
    """``metrics.time(...)`` when metrics are on, otherwise a free no-op."""
    if metrics is None:
        return nullcontext(Probe())
    return metrics.time(component, operation)


def summarise(samples: list[MetricSample]) -> list[MetricSummary]:
    """Group samples by component and operation."""
    groups: dict[tuple[str, str], list[MetricSample]] = defaultdict(list)
    for sample in samples:
        groups[(sample.component, sample.operation)].append(sample)
    return [
        MetricSummary(
            component=component,
            operation=operation,
            count=len(group),
            errors=sum(1 for s in group if s.outcome == "error"),
            median_ms=statistics.median(s.duration_ms for s in group),
            total_ms=sum(s.duration_ms for s in group),
            tokens_in=sum(s.tokens_in for s in group),
            tokens_out=sum(s.tokens_out for s in group),
            cost_usd=sum(s.cost_usd for s in group),
        )
        for (component, operation), group in sorted(groups.items())
    ]


def run_cost(samples: list[MetricSample]) -> float:
    """Total API cost of a run (FR-33)."""
    return sum(s.cost_usd for s in samples)
