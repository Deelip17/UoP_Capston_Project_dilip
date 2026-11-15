"""Edge cases for the healing helpers (branch coverage for NFR-18).

Requirements: FR-22 to FR-24, FR-25; NFR-18 (at least 90% for self-healing logic).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aitaf.core.errors import PersistenceError
from aitaf.core.healing import ElementSignature
from aitaf.core.llm import LlmRequest
from aitaf.core.models import HealingEvent, LocatorStrategy, Run, RunStatus
from aitaf.core.storage import InMemoryRepository
from aitaf.healing import (
    find_elements,
    mock_healing_responder,
    parse_dom,
    role_of,
    similarity,
    update_locator_from_event,
    validate_candidate,
)
from aitaf.healing.llm_step import build_prompt


@pytest.mark.whitebox
@pytest.mark.parametrize(
    ("tag", "attrs", "role"),
    [
        ("input", {"type": "submit"}, "button"),
        ("input", {"type": "checkbox"}, "checkbox"),
        ("input", {"type": "hidden"}, None),
        ("input", {}, "textbox"),
        ("a", {}, None),
        ("a", {"href": "/x"}, "link"),
        ("select", {}, "combobox"),
        ("h2", {}, "heading"),
        ("img", {}, "img"),
        ("div", {}, None),
        (None, {}, None),
        (None, {"role": "alert"}, "alert"),
    ],
)
def test_role_of(tag: str | None, attrs: dict[str, str], role: str | None) -> None:
    assert role_of(tag, attrs) == role


@pytest.mark.whitebox
def test_self_closing_tags_are_parsed_as_leaf_elements() -> None:
    dom = parse_dom("<p>one<br/>two</p><img src='x'/>")
    assert [e.tag for e in dom.elements] == ["p", "br", "img"]
    assert dom.elements[1].children == []


@pytest.mark.whitebox
@pytest.mark.parametrize("selector", ["   ", "a[href", "#", ".", "[", "a[", "'x", "a b >"])
def test_malformed_css_selectors_are_unsupported_not_errors(selector: str) -> None:
    dom = parse_dom("<a href='/x'>x</a>")
    assert find_elements(dom, LocatorStrategy(kind="css", value=selector)) is None


@pytest.mark.whitebox
def test_bare_attribute_selector_matches_on_presence() -> None:
    dom = parse_dom("<input type='text'><input>")
    found = find_elements(dom, LocatorStrategy(kind="css", value="[type]"))
    assert found is not None and len(found) == 1


@pytest.mark.whitebox
def test_the_style_attribute_is_ignored_when_comparing_attributes() -> None:
    dom = parse_dom("<button style='color:red'>Go</button>")
    expected = ElementSignature(attrs={"style": "color:blue"})
    assert similarity(expected, dom, dom.elements[0]) == 0.0


@pytest.mark.whitebox
def test_typing_into_a_disabled_field_is_refused() -> None:
    dom = parse_dom("<input disabled>")
    empty = ElementSignature()
    result = validate_candidate(empty, dom, dom.elements[0], "type")
    assert not result.passed and "disabled" in result.reasons[0]


def _prompt(candidates: list[str]) -> LlmRequest:
    intent = "Intent: click on the element named x\nExpected tag: button\nExpected text: go now"
    prompt = build_prompt(intent, "\n".join(candidates))
    return LlmRequest(component="self_healing", prompt_version="sh-v1", prompt=prompt)


@pytest.mark.whitebox
def test_mock_responder_prefers_an_id_then_a_class_then_the_bare_tag() -> None:
    with_id = mock_healing_responder(_prompt(['[1] <button> id="go" class="a" text="go now"']))
    with_class = mock_healing_responder(_prompt(['[1] <button> class="primary x" text="go now"']))
    bare = mock_healing_responder(_prompt(['[1] <button> text="go now"']))
    assert '"kind": "id", "value": "go"' in with_id
    assert '"kind": "css", "value": "button.primary"' in with_class
    assert '"kind": "css", "value": "button"' in bare


@pytest.mark.whitebox
def test_mock_responder_ignores_other_tags_and_admits_when_nothing_fits() -> None:
    reply = mock_healing_responder(_prompt(['[1] <a> id="link" text="go now"']))
    assert "no-such-element" in reply


@pytest.mark.whitebox
def test_applying_an_approved_event_for_an_unknown_locator_fails() -> None:
    repo = InMemoryRepository()
    now = datetime(2026, 11, 14, tzinfo=UTC)
    repo.create_run(
        Run(run_id="r", started_at=now, status=RunStatus.RUNNING, provider="mock", environment="t")
    )
    orphan = HealingEvent(
        event_id="e",
        run_id="r",
        step_ref="s",
        loc_id="nowhere.nothing",
        old_strategy=LocatorStrategy(kind="id", value="a"),
        new_strategy=LocatorStrategy(kind="id", value="b"),
        strategy_used="fallback",
        confidence=0.9,
        validated=True,
        outcome="proposed",
        approved=True,
        duration_ms=1,
        created_at=now,
    )
    repo.add_healing_event("r", orphan)
    with pytest.raises(PersistenceError, match="locator"):
        update_locator_from_event(repo, "r", "e")
