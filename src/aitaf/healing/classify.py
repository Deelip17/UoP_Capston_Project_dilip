"""Failure classification: locator failure versus application defect (FR-22).

Healing a genuine defect would hide a regression, so classification is the
precondition for safe repair. The exception type decides first (an assertion is
always a defect, even if its message mentions a missing element); the message is
consulted only for generic or framework-specific timeouts.
"""

from __future__ import annotations

from aitaf.core.healing import FailureKind

_LOCATOR_TYPES = frozenset(
    {
        "nosuchelementexception",
        "staleelementreferenceexception",
        "elementnotinteractableexception",
    }
)
_LOCATOR_PHRASES = (
    "waiting for locator",
    "waiting for selector",
    "no such element",
    "no locator strategy matched",
    "unable to locate element",
    "not attached to the dom",
    "stale element",
    "element not interactable",
    "element is not interactable",
)


def classify_failure(error_type: str, message: str) -> FailureKind:
    """Decide whether a failed step is a locator problem, a defect, or unknown."""
    name = error_type.rsplit(".", 1)[-1].strip().lower()
    text = message.strip().lower()
    if "assertion" in name:
        return FailureKind.APPLICATION_DEFECT
    if name in _LOCATOR_TYPES:
        return FailureKind.LOCATOR
    if text.startswith("assert"):
        return FailureKind.APPLICATION_DEFECT
    if any(phrase in text for phrase in _LOCATOR_PHRASES):
        return FailureKind.LOCATOR
    return FailureKind.UNKNOWN
