"""Human approval gate for permanent locator changes (FR-25, NFR-31).

A healed locator applies to the current run only. It reaches the locator
repository permanently only after a person approves the proposed event; a
permanent update without approval fails.
"""

from __future__ import annotations

from aitaf.core.errors import PersistenceError, PolicyError
from aitaf.core.logging import get_logger
from aitaf.core.models import HealingEvent, Locator
from aitaf.core.storage import Repository

_log = get_logger(__name__)


def _event(repo: Repository, run_id: str, event_id: str) -> HealingEvent:
    found = next((e for e in repo.list_healing_events(run_id) if e.event_id == event_id), None)
    if found is None:
        raise PersistenceError(f"unknown healing event: {event_id!r}")
    return found


def update_locator_from_event(repo: Repository, run_id: str, event_id: str) -> Locator:
    """Apply an approved event to the locator repository (new version, old primary kept)."""
    event = _event(repo, run_id, event_id)
    if not event.approved:
        raise PolicyError("permanent locator update needs human approval of the healing event")
    assert event.new_strategy is not None  # guaranteed: only proposed events can be approved
    current = next((loc for loc in repo.list_locators(run_id) if loc.loc_id == event.loc_id), None)
    if current is None:
        raise PersistenceError(f"unknown locator: {event.loc_id!r}")
    kept = [current.primary, *(f for f in current.fallbacks if f != event.new_strategy)]
    updated = current.model_copy(
        update={
            "primary": event.new_strategy,
            "fallbacks": [s for s in kept if s != event.new_strategy],
            "version": current.version + 1,
        }
    )
    repo.add_locator(run_id, updated)
    _log.info(
        "locator %s updated to version %d from event %s", updated.loc_id, updated.version, event_id
    )
    return updated


def approve_healing_event(repo: Repository, run_id: str, event_id: str) -> Locator:
    """Human decision: approve a validated, proposed event and apply it permanently."""
    event = _event(repo, run_id, event_id)
    if event.outcome != "proposed" or not event.validated:
        raise PolicyError("only validated, proposed healing events can be approved")
    if not any(loc.loc_id == event.loc_id for loc in repo.list_locators(run_id)):
        raise PersistenceError(f"unknown locator: {event.loc_id!r}")
    repo.add_healing_event(run_id, event.model_copy(update={"approved": True}))
    return update_locator_from_event(repo, run_id, event_id)
