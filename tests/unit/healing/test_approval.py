"""Human approval gate for permanent locator changes, and healing metrics.

Requirements: FR-25 (persist every healing event as proposed; update the locator
repository permanently only after human approval; a permanent update without
approval fails), FR-26 (healing success rate), NFR-31 (no unapproved permanent
change).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aitaf.core.errors import PersistenceError, PolicyError
from aitaf.core.healing import FailureContext
from aitaf.core.logging import set_run_id
from aitaf.core.models import HealingEvent, Locator, LocatorStrategy, Run, RunStatus
from aitaf.core.storage import InMemoryRepository
from aitaf.healing import (
    SelfHealingEngine,
    approve_healing_event,
    parse_dom,
    signature_of,
    success_rates,
    update_locator_from_event,
)

DATA = Path(__file__).resolve().parents[3] / "data" / "dom"
NOW = datetime(2026, 11, 14, tzinfo=UTC)

LOCATOR = Locator(
    loc_id="login.login_button",
    page="login",
    name="login_button",
    primary=LocatorStrategy(kind="id", value="login-button"),
    fallbacks=[LocatorStrategy(kind="css", value="button[type=submit]")],
    model="mock-1",
    prompt_version="sg-v1",
)


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
    repository.add_locator("run-1", LOCATOR)
    set_run_id("run-1")
    yield repository
    set_run_id("")


def heal_once(repo: InMemoryRepository, page: str = "login_id_changed.html") -> HealingEvent:
    before = parse_dom((DATA / "login_before.html").read_text(encoding="utf-8"))
    baseline = signature_of(before, next(e for e in before.elements if e.tag == "button"))
    context = FailureContext(
        step_ref="TC-1:step3",
        action="click",
        locator=LOCATOR,
        error_type="NoSuchElementException",
        error_message="",
        dom_html=(DATA / page).read_text(encoding="utf-8"),
        baseline=baseline,
    )
    return SelfHealingEngine(repo).heal(context).events[0]


def event(
    event_id: str,
    step: str,
    strategy: str,
    outcome: str,
    validated: bool = False,
) -> HealingEvent:
    return HealingEvent(
        event_id=event_id,
        run_id="run-1",
        step_ref=step,
        loc_id="login.login_button",
        old_strategy=LocatorStrategy(kind="id", value="a"),
        new_strategy=LocatorStrategy(kind="id", value="b") if outcome != "no_candidate" else None,
        strategy_used=strategy,  # type: ignore[arg-type]
        confidence=0.8,
        validated=validated,
        outcome=outcome,  # type: ignore[arg-type]
        duration_ms=1,
        created_at=NOW,
    )


@pytest.mark.blackbox
def test_a_healed_locator_is_not_changed_permanently_without_approval(
    repo: InMemoryRepository,
) -> None:
    proposed = heal_once(repo)
    assert not proposed.approved
    with pytest.raises(PolicyError, match="approval"):
        update_locator_from_event(repo, "run-1", proposed.event_id)
    stored = repo.list_locators("run-1")[0]
    assert stored.version == 1 and stored.primary.value == "login-button"


@pytest.mark.blackbox
def test_approval_updates_the_locator_repository_and_keeps_the_old_primary_as_fallback(
    repo: InMemoryRepository,
) -> None:
    proposed = heal_once(repo)
    updated = approve_healing_event(repo, "run-1", proposed.event_id)
    assert updated.version == 2
    assert updated.primary == LocatorStrategy(kind="css", value="button[type=submit]")
    assert updated.fallbacks == [LocatorStrategy(kind="id", value="login-button")]
    assert repo.list_locators("run-1") == [updated]
    stored_event = repo.list_healing_events("run-1")[0]
    assert stored_event.approved and stored_event.outcome == "proposed"


@pytest.mark.blackbox
def test_an_event_of_an_execution_run_updates_the_locator_of_the_script_run(
    repo: InMemoryRepository,
) -> None:
    """The approval gap: the event belongs to the execution run, the locator to run-1."""
    repo.create_run(
        Run(
            run_id="run-exec",
            started_at=NOW,
            status=RunStatus.COMPLETED,
            provider="mock",
            environment="t",
        )
    )
    repo.add_healing_event(
        "run-exec",
        event("e-exec", "t.py::t#login.login_button", "similarity", "proposed", True).model_copy(
            update={"run_id": "run-exec"}
        ),
    )
    with pytest.raises(PersistenceError, match="unknown locator"):
        approve_healing_event(repo, "run-exec", "e-exec")
    updated = approve_healing_event(repo, "run-exec", "e-exec", "run-1")
    assert updated.version == 2 and updated.primary == LocatorStrategy(kind="id", value="b")
    assert repo.list_locators("run-1") == [updated]
    assert repo.list_healing_events("run-exec")[0].approved


@pytest.mark.blackbox
def test_only_validated_proposed_events_can_be_approved(repo: InMemoryRepository) -> None:
    repo.add_healing_event("run-1", event("e-rej", "s", "similarity", "rejected"))
    repo.add_healing_event("run-1", event("e-none", "s", "llm", "no_candidate"))
    for event_id in ("e-rej", "e-none"):
        with pytest.raises(PolicyError, match="proposed"):
            approve_healing_event(repo, "run-1", event_id)
    assert repo.list_locators("run-1")[0].version == 1


@pytest.mark.whitebox
def test_unknown_event_or_locator_is_reported(repo: InMemoryRepository) -> None:
    with pytest.raises(PersistenceError, match="healing event"):
        approve_healing_event(repo, "run-1", "missing")
    orphan = event("e-orphan", "s", "fallback", "proposed", validated=True).model_copy(
        update={"loc_id": "nowhere.nothing"}
    )
    repo.add_healing_event("run-1", orphan)
    with pytest.raises(PersistenceError, match="locator"):
        approve_healing_event(repo, "run-1", "e-orphan")


@pytest.mark.whitebox
def test_the_old_primary_is_not_duplicated_in_the_fallbacks(repo: InMemoryRepository) -> None:
    repo.add_locator(
        "run-1",
        LOCATOR.model_copy(
            update={
                "fallbacks": [
                    LocatorStrategy(kind="css", value="button[type=submit]"),
                    LocatorStrategy(kind="text", value="Sign in"),
                ]
            }
        ),
    )
    proposed = heal_once(repo)
    updated = approve_healing_event(repo, "run-1", proposed.event_id)
    assert [f.kind for f in updated.fallbacks] == ["id", "text"]


@pytest.mark.blackbox
def test_success_rates_overall_and_per_strategy() -> None:
    events = [
        event("1", "s1", "fallback", "proposed", True),
        event("2", "s2", "fallback", "proposed", True),
        event("3", "s3", "fallback", "proposed", True),
        event("4", "s4", "fallback", "rejected"),
        event("5", "s4", "similarity", "rejected"),
        event("6", "s5", "similarity", "rejected"),
        event("7", "s5", "llm", "proposed", True),
        event("8", "s6", "fallback", "no_candidate"),
    ]
    rates = success_rates(events)
    assert rates["fallback"] == pytest.approx(0.75)
    assert rates["similarity"] == 0.0
    assert rates["llm"] == 1.0
    assert rates["overall"] == pytest.approx(4 / 6)


@pytest.mark.whitebox
def test_success_rates_of_nothing_are_empty() -> None:
    assert success_rates([]) == {}
    assert success_rates([event("1", "s", "llm", "no_candidate")]) == {"overall": 0.0}
