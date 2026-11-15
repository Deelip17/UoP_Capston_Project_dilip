"""Locator-healing interface shared by the Execution Engine and the Self-Healing Engine.

It lives in ``core`` so the Execution Engine can call a healer without importing
the Self-Healing Engine (NFR-17, no circular dependency). Requirements: FR-22
(failure kinds), FR-23 and FR-24 (repair and validation outcome), FR-25 (events).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from aitaf.core.models import HealingEvent, Locator, LocatorStrategy


class FailureKind(StrEnum):
    """Why a step failed, as far as healing is concerned (FR-22)."""

    LOCATOR = "locator"
    APPLICATION_DEFECT = "application_defect"
    UNKNOWN = "unknown"


class HealStatus(StrEnum):
    """Result of one healing request."""

    HEALED = "healed"
    NOT_HEALED = "not_healed"
    NOT_HEALABLE = "not_healable"
    LIMIT_REACHED = "limit_reached"


@dataclass(frozen=True)
class ElementSignature:
    """What the original element looked like: tag, attributes, text and surroundings."""

    tag: str | None = None
    attrs: dict[str, str] = field(default_factory=dict)
    text: str = ""
    ancestors: tuple[str, ...] = ()
    neighbours: tuple[str, ...] = ()


@dataclass(frozen=True)
class FailureContext:
    """Everything the healer needs about one failed step."""

    step_ref: str
    action: str
    locator: Locator
    error_type: str
    error_message: str
    dom_html: str
    baseline: ElementSignature | None = None


@dataclass
class HealResult:
    """Outcome of a healing request: a proposed replacement locator or a reason why not."""

    status: HealStatus
    kind: FailureKind
    strategy: LocatorStrategy | None = None
    confidence: float = 0.0
    events: list[HealingEvent] = field(default_factory=list)
    reason: str = ""


class LocatorHealer(Protocol):
    """Called by the Execution Engine when a step fails."""

    def heal(self, ctx: FailureContext) -> HealResult:
        """Try to repair the step's locator without hiding a real defect."""
