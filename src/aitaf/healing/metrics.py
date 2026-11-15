"""Healing success rates (FR-26, FR-33, FR-39).

Overall rate: steps with a validated proposal divided by steps for which healing
was attempted. Per-strategy rate: how often a candidate that the rung offered
survived validation (rungs that found nothing are not counted against it).
"""

from __future__ import annotations

from collections import defaultdict

from aitaf.core.models import HealingEvent


def success_rates(events: list[HealingEvent]) -> dict[str, float]:
    """Return ``{"overall": rate, "<strategy>": rate, ...}``; empty if nothing was attempted."""
    if not events:
        return {}
    steps = {e.step_ref for e in events}
    healed = {e.step_ref for e in events if e.outcome == "proposed"}
    rates: dict[str, float] = {"overall": len(healed) / len(steps)}
    offered: dict[str, list[bool]] = defaultdict(list)
    for event in events:
        if event.outcome in ("proposed", "rejected"):
            offered[event.strategy_used].append(event.outcome == "proposed")
    for strategy, outcomes in offered.items():
        rates[strategy] = sum(outcomes) / len(outcomes)
    return rates
