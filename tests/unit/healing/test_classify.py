"""Failure classification: locator failure versus application defect.

Requirements: FR-22 (detect a locator failure - element not found, stale or not
interactable - and distinguish it from an application defect).
"""

from __future__ import annotations

import pytest

from aitaf.core.healing import FailureKind
from aitaf.healing import classify_failure

LOCATOR = [
    ("NoSuchElementException", "Message: no such element: Unable to locate element"),
    ("selenium.common.exceptions.NoSuchElementException", ""),
    ("StaleElementReferenceException", "stale element reference: element is not attached"),
    ("ElementNotInteractableException", "element not interactable"),
    ("TimeoutError", "Timeout 30000ms exceeded. waiting for locator('#login-button')"),
    ("playwright._impl._errors.TimeoutError", "Timeout 5000ms exceeded while waiting for selector"),
    ("Error", "Element is not attached to the DOM"),
    ("TimeoutException", "no such element: unable to locate element: css selector"),
    ("ElementNotInteractableException", "Message: element not interactable"),
    ("LookupError", "no locator strategy matched for login_submit on page login"),
]
DEFECT = [
    ("AssertionError", "assert 'Welcome' in 'Error: invalid password'"),
    ("AssertionError", "no such element in the order table"),
    ("pytest.fail.Exception", "assert response.status == 200"),
    ("AssertionError", "Element is not attached to the DOM"),
]
UNKNOWN = [
    ("ConnectionError", "connection refused"),
    ("TimeoutError", "Timeout 30000ms exceeded."),
    ("ValueError", "bad literal"),
    ("ElementClickInterceptedException", "another element would receive the click"),
    ("", ""),
]


@pytest.mark.blackbox
@pytest.mark.parametrize(("error_type", "message"), LOCATOR)
def test_locator_failures_are_detected(error_type: str, message: str) -> None:
    assert classify_failure(error_type, message) is FailureKind.LOCATOR


@pytest.mark.blackbox
@pytest.mark.parametrize(("error_type", "message"), DEFECT)
def test_assertion_failures_are_application_defects_even_with_locator_words(
    error_type: str, message: str
) -> None:
    assert classify_failure(error_type, message) is FailureKind.APPLICATION_DEFECT


@pytest.mark.blackbox
@pytest.mark.parametrize(("error_type", "message"), UNKNOWN)
def test_other_failures_are_unknown_and_never_healed(error_type: str, message: str) -> None:
    assert classify_failure(error_type, message) is FailureKind.UNKNOWN


@pytest.mark.whitebox
def test_error_type_wins_over_message() -> None:
    assert (
        classify_failure("AssertionError", "waiting for locator('#x')")
        is FailureKind.APPLICATION_DEFECT
    )
    assert classify_failure("NoSuchElementException", "assert failed") is FailureKind.LOCATOR


@pytest.mark.whitebox
def test_classification_is_case_insensitive_and_strips_module_path() -> None:
    assert classify_failure("my.pkg.NOSUCHELEMENTEXCEPTION", "") is FailureKind.LOCATOR
    assert classify_failure("x.y.assertionerror", "") is FailureKind.APPLICATION_DEFECT
