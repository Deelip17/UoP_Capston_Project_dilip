"""Validation of a healed element before it is accepted (FR-24, NFR-31).

A healed locator must find an element with the same role, similar text and the
same context as the original, and the element must suit the step's action. This
is what rejects a present-but-wrong element, so the step still fails instead of
passing for the wrong reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from aitaf.core.healing import ElementSignature
from aitaf.healing.dom import Dom, DomElement, role_of
from aitaf.healing.similarity import candidate_text, context_score, text_ratio

TEXT_MATCH = 0.5
CONTEXT_MATCH = 0.3
_NON_TEXT_INPUTS = frozenset(
    {"checkbox", "radio", "button", "submit", "reset", "image", "file", "hidden", "range", "color"}
)


_OPPOSITES = (
    ("add", "remove"),
    ("open", "close"),
    ("show", "hide"),
    ("enable", "disable"),
    ("login", "logout"),
    ("signin", "signout"),
    ("increase", "decrease"),
    ("start", "stop"),
    ("create", "delete"),
    ("expand", "collapse"),
    ("next", "previous"),
    ("accept", "reject"),
)
_INTENT_ATTRS = ("id", "name", "class", "data-qa", "data-testid", "aria-label", "title", "value")
_WORDS = re.compile(r"[a-z]+")


def _intent_words(attrs: dict[str, str], text: str) -> set[str]:
    """Lower-case words from the identifying attributes and the visible text."""
    parts = [attrs.get(name, "") for name in _INTENT_ATTRS] + [text]
    return set(_WORDS.findall(" ".join(parts).lower().replace("_", " ")))


def _intent_conflict(expected: ElementSignature, candidate: DomElement) -> str | None:
    """Reject a candidate that does the opposite of the original (add versus remove, ...).

    Found in Unit 6: a "remove" button was repaired to the "add" button because their ids
    look alike. The check fires only if the original names one word of a pair, the
    candidate names the other, and neither names both.
    """
    wanted = _intent_words(expected.attrs, expected.text)
    found = _intent_words(candidate.attrs, candidate_text(candidate))
    for left, right in _OPPOSITES:
        for have, other in ((left, right), (right, left)):
            if have in wanted and other not in wanted and other in found and have not in found:
                return f"intent mismatch: expected '{have}', found '{other}'"
    return None


@dataclass(frozen=True)
class Validation:
    """Verdict with the reason for every failed check."""

    passed: bool
    reasons: list[str] = field(default_factory=list)


def _hidden(element: DomElement) -> bool:
    style = element.attrs.get("style", "").replace(" ", "").lower()
    return (
        "hidden" in element.attrs
        or element.attrs.get("type", "").lower() == "hidden"
        or "display:none" in style
    )


def _accepts_typing(element: DomElement) -> bool:
    if "contenteditable" in element.attrs:
        return True
    if element.tag == "textarea":
        return True
    return (
        element.tag == "input" and element.attrs.get("type", "text").lower() not in _NON_TEXT_INPUTS
    )


def _action_problem(action: str, element: DomElement) -> str | None:
    if action == "click":
        if "disabled" in element.attrs:
            return "action mismatch: element is disabled"
        if _hidden(element):
            return "action mismatch: element is hidden"
    elif action == "type":
        if not _accepts_typing(element):
            return f"action mismatch: cannot type into <{element.tag}>"
        if "disabled" in element.attrs:
            return "action mismatch: element is disabled"
    elif action == "select":
        if element.tag != "select":
            return f"action mismatch: <{element.tag}> is not a select element"
    elif action == "assert_visible" and _hidden(element):
        return "action mismatch: element is hidden"
    return None


def validate_candidate(
    expected: ElementSignature, dom: Dom, candidate: DomElement, action: str
) -> Validation:
    """Check role, text, context and action fit; report every failure."""
    reasons: list[str] = []

    wanted_role = role_of(expected.tag, expected.attrs)
    found_role = role_of(candidate.tag, candidate.attrs)
    if wanted_role and wanted_role != found_role:
        reasons.append(f"role mismatch: expected {wanted_role}, found {found_role or 'none'}")

    if expected.text and text_ratio(expected.text, candidate_text(candidate)) < TEXT_MATCH:
        shown = candidate_text(candidate)[:40]
        reasons.append(f"text mismatch: expected '{expected.text[:40]}', found '{shown}'")

    context = context_score(expected, dom, candidate)
    if context is not None and context < CONTEXT_MATCH:
        reasons.append(f"context mismatch: score {context:.2f} below {CONTEXT_MATCH}")

    conflict = _intent_conflict(expected, candidate)
    if conflict:
        reasons.append(conflict)

    problem = _action_problem(action, candidate)
    if problem:
        reasons.append(problem)
    return Validation(passed=not reasons, reasons=reasons)
