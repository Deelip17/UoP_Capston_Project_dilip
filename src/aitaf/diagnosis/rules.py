"""Deterministic pre-classifier (FR-27, FR-28).

Ordered rules over the exception type, the short exception text and the log decide
the cheap, clear cases without a model. The order matters: an environment signal
(for example ``net::ERR_CONNECTION_REFUSED`` inside a timeout) beats a timeout, a
locator failure beats a timeout that is waiting for a locator, and an assertion is
always an application defect even if its message mentions a missing element. A
failure no rule recognises is returned as ``None`` and left to the model.

The matching phrases for locator failures are written out here on purpose: a
component may import only ``core`` (NFR-17), not the healing package.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from aitaf.core.masking import mask
from aitaf.core.models import FailureCategory

_QUOTE_CAP = 120
_PAGE_OBJECT_MISS = re.compile(r"no locator strategy matched for (\w+) on page (\w+)")
_NET_ERROR = re.compile(r"net::err_\w+")

_ENV_TYPES = (
    "connectionrefusederror",
    "connectionreseterror",
    "connectionabortederror",
    "connectionerror",
    "brokenpipeerror",
    "sslerror",
    "oserror",
    "permissionerror",
)
_ENV_PHRASES = (
    "net::err_",
    "connection refused",
    "econnrefused",
    "name or service not known",
    "getaddrinfo",
    "target page, context or browser has been closed",
    "browser has been closed",
    "target closed",
    "page crashed",
    "no space left",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "internal server error",
    "certificate verify failed",
)
_LOCATOR_TYPES = (
    "nosuchelementexception",
    "staleelementreferenceexception",
    "elementnotinteractableexception",
)
_LOCATOR_PHRASES = (
    "no locator strategy matched",
    "waiting for locator",
    "waiting for selector",
    "no such element",
    "unable to locate element",
    "not attached to the dom",
    "stale element",
    "element not interactable",
    "element is not interactable",
    "strict mode violation",
)
_DATA_TYPES = ("keyerror", "filenotfounderror")
_DATA_PHRASES = (
    "test data",
    "dataset",
    "already exists",
    "duplicate",
    "unique constraint",
    "409",
    "conflict",
)


@dataclass(frozen=True)
class FailureFacts:
    """What the rules look at for one failed or errored test."""

    status: str
    error_type: str
    error_text: str
    log: str = ""
    attempts: int = 1
    healing_outcomes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Verdict:
    """A rule's decision with its explanation and next step."""

    category: FailureCategory
    confidence: float
    rule: str
    cause: str
    remediation: str


def _short(text: str) -> str:
    return mask(" ".join(text.split())[:_QUOTE_CAP]).text


def _first(haystack: str, phrases: tuple[str, ...]) -> str | None:
    return next((p for p in phrases if p in haystack), None)


def _healing_sentence(outcomes: tuple[str, ...], category: str) -> str:
    if not outcomes:
        return ""
    listed = ", ".join(outcomes)
    sentence = f" Self-healing was attempted ({len(outcomes)} event(s): {listed})."
    if "proposed" in outcomes:
        sentence += (
            " A healed locator was proposed but the test still failed."
            if category == "locator"
            else " A healed locator was proposed and applied, so the locator is probably not "
            "the cause."
        )
    return sentence


def classify(facts: FailureFacts) -> Verdict | None:
    """Return a verdict for a clear failure, or None if no rule applies."""
    kind = facts.error_type.rsplit(".", 1)[-1].strip().lower()
    text = facts.error_text.lower()
    hay = f"{kind} {text} {facts.log.lower()}"
    healing = facts.healing_outcomes

    signal = _first(hay, _ENV_PHRASES) or (kind if kind in _ENV_TYPES else None)
    network = _NET_ERROR.search(hay)
    if network:
        signal = network.group(0)[:5] + network.group(0)[5:].upper()
    if signal:
        return Verdict(
            "environment",
            0.85,
            "environment-signal",
            f"The environment or infrastructure failed ('{signal}'), not the logic under test."
            + _healing_sentence(healing, "environment"),
            "Check that the system under test, the network and the browser are running and "
            "reachable, then rerun.",
        )

    if "assertion" in kind or text.strip().startswith("assert") or kind == "failed":
        return Verdict(
            "assertion_defect",
            0.9 if facts.attempts > 1 else 0.85,
            "assertion",
            "The application behaved differently from what the test expects: "
            f"{_short(facts.error_text) or 'an assertion failed'}."
            + _healing_sentence(healing, "assertion_defect"),
            "Reproduce the step by hand; if the behaviour is wrong report a defect, otherwise "
            "update the expected value in the test.",
        )

    miss = _PAGE_OBJECT_MISS.search(text)
    if miss or kind in _LOCATOR_TYPES or _first(hay, _LOCATOR_PHRASES):
        if miss:
            cause = (
                f"The element '{miss.group(1)}' on page '{miss.group(2)}' was not found: "
                "the stored locator no longer matches the page."
            )
            confidence = 0.9
        else:
            cause = "An element could not be found with the stored locator: the page changed."
            confidence = 0.8
        return Verdict(
            "locator",
            confidence,
            "locator-miss",
            cause + _healing_sentence(healing, "locator"),
            "Run with --heal and review the proposed locator, or update the locator in the page "
            "object; if the element was removed on purpose, update the test.",
        )

    data = _first(text, _DATA_PHRASES) or (kind if kind in _DATA_TYPES else None)
    if data:
        return Verdict(
            "test_data",
            0.7 if data in _DATA_PHRASES else 0.6,
            "test-data",
            f"The test data was missing, malformed or conflicting ('{data}')."
            + _healing_sentence(healing, "test_data"),
            "Check the data set for this test case (keys, files, unique values) and correct or "
            "regenerate it.",
        )

    if "timeout" in kind or "timeout" in text or "timed out" in text:
        return Verdict(
            "timing_flaky",
            0.7 if facts.attempts > 1 else 0.6,
            "timeout",
            "An operation timed out: the page or system may be slow, or the test does not wait "
            "for the right condition." + _healing_sentence(healing, "timing_flaky"),
            "Rerun to see whether it recurs, wait for an explicit condition instead of a fixed "
            "delay, or raise the timeout.",
        )
    return None
