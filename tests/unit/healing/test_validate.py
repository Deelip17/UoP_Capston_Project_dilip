"""Validation of a healed element before it is accepted.

Requirements: FR-24 (validate a healed locator by checking that the element's
role, text and context match the original; reject a present-but-wrong element),
NFR-31 (no unapproved or wrong change goes through).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.core.healing import ElementSignature
from aitaf.healing import parse_dom, signature_of, validate_candidate

DATA = Path(__file__).resolve().parents[3] / "data" / "dom"


def dom_of(name: str):  # type: ignore[no-untyped-def]
    return parse_dom((DATA / name).read_text(encoding="utf-8"))


BEFORE = dom_of("login_before.html")
BASELINE = signature_of(BEFORE, next(e for e in BEFORE.elements if e.tag == "button"))


def button_in(dom):  # type: ignore[no-untyped-def]
    return next(e for e in dom.elements if e.tag == "button")


@pytest.mark.blackbox
@pytest.mark.parametrize(
    "page", ["login_id_changed.html", "login_all_changed.html", "login_wrapped.html"]
)
def test_the_same_button_after_a_mutation_is_accepted(page: str) -> None:
    dom = dom_of(page)
    result = validate_candidate(BASELINE, dom, button_in(dom), "click")
    assert result.passed, result.reasons


@pytest.mark.blackbox
def test_a_present_but_wrong_element_is_rejected_on_text() -> None:
    dom = dom_of("login_wrong_element.html")
    result = validate_candidate(BASELINE, dom, button_in(dom), "click")
    assert not result.passed
    assert any("text" in reason for reason in result.reasons)


@pytest.mark.blackbox
def test_an_element_with_the_wrong_role_is_rejected() -> None:
    link = next(e for e in BEFORE.elements if e.tag == "a")
    result = validate_candidate(BASELINE, BEFORE, link, "click")
    assert not result.passed
    assert any("role" in reason for reason in result.reasons)


@pytest.mark.blackbox
def test_an_element_in_the_wrong_context_is_rejected() -> None:
    moved = parse_dom("<footer><div><span><button>Sign in</button></span></div></footer>")
    button = next(e for e in moved.elements if e.tag == "button")
    result = validate_candidate(BASELINE, moved, button, "click")
    assert not result.passed
    assert any("context" in reason for reason in result.reasons)


@pytest.mark.whitebox
def test_every_failed_check_is_reported() -> None:
    dom = parse_dom("<footer><a href='/x'>Cancel everything</a></footer>")
    result = validate_candidate(
        BASELINE, dom, next(e for e in dom.elements if e.tag == "a"), "click"
    )
    joined = " ".join(result.reasons)
    assert "role" in joined and "text" in joined and "context" in joined


@pytest.mark.whitebox
@pytest.mark.parametrize(
    ("html", "tag", "action", "passed"),
    [
        ("<button disabled>x</button>", "button", "click", False),
        ("<button hidden>x</button>", "button", "click", False),
        ("<button>x</button>", "button", "click", True),
        ("<button>x</button>", "button", "type", False),
        ('<input type="email">', "input", "type", True),
        ('<input type="checkbox">', "input", "type", False),
        ("<textarea></textarea>", "textarea", "type", True),
        ("<div contenteditable>x</div>", "div", "type", True),
        ('<input type="text">', "input", "select", False),
        ("<select><option>a</option></select>", "select", "select", True),
        ('<input type="hidden">', "input", "assert_visible", False),
        ("<p>hello</p>", "p", "assert_visible", True),
        ("<p>hello</p>", "p", "assert_text", True),
        ("<p>hello</p>", "p", "open", True),
    ],
)
def test_the_element_must_suit_the_action(html: str, tag: str, action: str, passed: bool) -> None:
    dom = parse_dom(html)
    element = next(e for e in dom.elements if e.tag == tag)
    empty = ElementSignature(tag=None, attrs={}, text="")
    assert validate_candidate(empty, dom, element, action).passed is passed


@pytest.mark.whitebox
def test_a_signature_without_information_does_not_contradict_the_candidate() -> None:
    empty = ElementSignature(tag=None, attrs={}, text="")
    button = button_in(BEFORE)
    assert validate_candidate(empty, BEFORE, button, "click").passed


@pytest.mark.whitebox
def test_role_is_taken_from_an_explicit_role_attribute_first() -> None:
    dom = parse_dom('<a role="button" href="/x">Sign in</a>')
    expected = ElementSignature(tag="button", attrs={}, text="Sign in")
    assert validate_candidate(expected, dom, dom.elements[0], "click").passed


# ------------------------------------------------------------ intent guard (D-002)


def expected_of(html: str) -> ElementSignature:
    dom = parse_dom(html)
    return signature_of(dom, next(e for e in dom.elements if e.tag == "button"))


@pytest.mark.blackbox
def test_a_candidate_with_the_opposite_action_is_rejected() -> None:
    """A "remove" button must not be repaired to an "add" button (found in Unit 6)."""
    expected = expected_of('<button id="remove-backpack" type="submit">Remove</button>')
    page = parse_dom('<button id="add-backpack" type="submit">Add to cart</button>')
    result = validate_candidate(expected, page, button_in(page), "click")
    assert not result.passed
    assert any("intent mismatch" in reason for reason in result.reasons)


@pytest.mark.blackbox
def test_the_guard_works_from_the_locator_words_without_visible_text() -> None:
    expected = ElementSignature(tag="button", attrs={"id": "add_backpack"})
    page = parse_dom('<button id="remove-backpack" type="submit">Remove</button>')
    result = validate_candidate(expected, page, button_in(page), "click")
    assert any("intent mismatch" in reason for reason in result.reasons)


@pytest.mark.whitebox
@pytest.mark.parametrize(
    ("wanted", "found"),
    [
        ("open-menu", "close-menu"),
        ("show-details", "hide-details"),
        ("enable-sound", "disable-sound"),
        ("login-button", "logout-button"),
        ("create-item", "delete-item"),
    ],
)
def test_other_opposite_pairs_are_caught(wanted: str, found: str) -> None:
    expected = ElementSignature(tag="button", attrs={"id": wanted})
    page = parse_dom(f'<button id="{found}" type="button">x</button>')
    result = validate_candidate(expected, page, button_in(page), "click")
    assert any("intent mismatch" in reason for reason in result.reasons)


@pytest.mark.whitebox
def test_the_same_intent_with_a_new_id_is_not_flagged() -> None:
    expected = expected_of('<button id="add-backpack" type="submit">Add to cart</button>')
    page = parse_dom('<button id="buy-backpack" class="btn-add" type="submit">Add to cart</button>')
    result = validate_candidate(expected, page, button_in(page), "click")
    assert not any("intent mismatch" in reason for reason in result.reasons)


@pytest.mark.whitebox
def test_a_candidate_naming_both_words_is_not_flagged() -> None:
    expected = ElementSignature(tag="button", attrs={"id": "add-item"})
    page = parse_dom('<button id="add-or-remove-item" type="button">Add or remove</button>')
    result = validate_candidate(expected, page, button_in(page), "click")
    assert not any("intent mismatch" in reason for reason in result.reasons)
