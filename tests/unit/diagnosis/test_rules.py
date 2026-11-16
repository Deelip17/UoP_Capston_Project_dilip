"""Deterministic pre-classifier of the Failure Analyzer (FR-27, FR-28, FR-29).

The labelled cases below are **unit-test fixtures written together with the rules**.
They prove that every rule fires and that no failure is left without an answer; they
are not the evaluation set for objective O4, which the author labels separately
before the classifier is run on it.
"""

from __future__ import annotations

import pytest

from aitaf.diagnosis.rules import FailureFacts, classify

LOCATOR = [
    ("LookupError", "no locator strategy matched for login_submit on page login"),
    ("NoSuchElementException", "Message: no such element: Unable to locate element"),
    ("StaleElementReferenceException", "stale element reference: element is not attached"),
    ("ElementNotInteractableException", "element not interactable"),
    ("Error", "strict mode violation: locator('button') resolved to 3 elements"),
]
ASSERTION = [
    ("AssertionError", "assert 'Sign in' in 'Log in'"),
    ("AssertionError", "Locator expected to be visible"),
    ("AssertionError", "wrong total"),
    ("pytest.fail.Exception", "assert response.status == 200"),
]
ENVIRONMENT = [
    ("Error", "page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8765/"),
    ("ConnectionRefusedError", "[Errno 111] Connection refused"),
    ("Error", "Target page, context or browser has been closed"),
    ("TimeoutError", "page.goto: net::ERR_NAME_NOT_RESOLVED"),
    ("WebDriverException", "Message: unknown error: net::ERR_INTERNET_DISCONNECTED"),
    ("HTTPError", "503 Service Unavailable"),
    ("SSLError", "certificate verify failed"),
    ("OSError", "[Errno 28] No space left on device"),
]
TEST_DATA = [
    ("KeyError", "'email'"),
    ("FileNotFoundError", "[Errno 2] No such file or directory: 'data/customers.csv'"),
    ("ValueError", "invalid test data: dataset has no value for 'postcode'"),
    ("HTTPError", "409 Conflict: a customer with this email already exists"),
]
TIMING = [
    ("TimeoutError", "Timeout 30000ms exceeded."),
    ("TimeoutException", "Message: timed out after 10 seconds"),
    ("Error", "page.goto: Timeout 30000ms exceeded."),
]
AMBIGUOUS = [
    ("RuntimeError", "unexpected state"),
    ("ZeroDivisionError", "division by zero"),
    ("", ""),
]


def facts(error_type: str, text: str, **extra: object) -> FailureFacts:
    base: dict[str, object] = {
        "status": "failed",
        "error_type": error_type,
        "error_text": text,
        "log": text,
    }
    return FailureFacts(**{**base, **extra})  # type: ignore[arg-type]


def labelled() -> list[tuple[str, str, str]]:
    groups = [
        ("locator", LOCATOR),
        ("assertion_defect", ASSERTION),
        ("environment", ENVIRONMENT),
        ("test_data", TEST_DATA),
        ("timing_flaky", TIMING),
    ]
    return [(label, kind, text) for label, items in groups for kind, text in items]


@pytest.mark.blackbox
@pytest.mark.parametrize(("label", "kind", "text"), labelled(), ids=lambda v: str(v)[:40])
def test_every_labelled_failure_gets_its_category(label: str, kind: str, text: str) -> None:
    verdict = classify(facts(kind, text))
    assert verdict is not None
    assert verdict.category == label


@pytest.mark.blackbox
@pytest.mark.parametrize(("kind", "text"), AMBIGUOUS, ids=lambda v: repr(v)[:30])
def test_failures_no_rule_recognises_are_left_to_the_model(kind: str, text: str) -> None:
    assert classify(facts(kind, text)) is None


@pytest.mark.blackbox
@pytest.mark.parametrize(("label", "kind", "text"), labelled(), ids=lambda v: str(v)[:40])
def test_every_verdict_has_a_cause_a_next_step_and_a_bounded_confidence(
    label: str, kind: str, text: str
) -> None:
    verdict = classify(facts(kind, text))
    assert verdict is not None
    assert verdict.cause.strip() and verdict.remediation.strip()
    assert 0.0 <= verdict.confidence <= 1.0
    assert verdict.rule


@pytest.mark.whitebox
def test_a_network_error_inside_a_timeout_is_environment_not_timing() -> None:
    verdict = classify(facts("TimeoutError", "page.goto: net::ERR_CONNECTION_TIMED_OUT"))
    assert verdict is not None and verdict.category == "environment"


@pytest.mark.whitebox
def test_a_raw_wait_that_ran_out_of_time_is_timing_even_when_it_names_a_locator() -> None:
    # decided after the first evaluation (author's labels): the wait may fail because the page
    # was slow, so the type TimeoutError wins; a page-object miss is still a locator failure
    verdict = classify(facts("TimeoutError", "Timeout 5000ms exceeded waiting for selector '#x'"))
    assert verdict is not None and verdict.category == "timing_flaky"
    miss = classify(facts("LookupError", "no locator strategy matched for x on page shop"))
    assert miss is not None and miss.category == "locator"


@pytest.mark.whitebox
def test_an_http_error_status_assertion_is_environment() -> None:
    verdict = classify(facts("AssertionError", "assert 404 == 200 + where 404 = <Response>"))
    assert verdict is not None and verdict.category == "environment"
    other = classify(facts("AssertionError", "assert 3 == 4"))
    assert other is not None and other.category == "assertion_defect"


@pytest.mark.whitebox
def test_a_validation_message_in_the_assertion_or_the_page_is_test_data() -> None:
    msg = "assert 'Thank you' in 'Name required'"
    verdict = classify(facts("AssertionError", msg))
    assert verdict is not None and verdict.category == "test_data"
    page = FailureFacts(
        "failed", "AssertionError", "assert False", page_text="Bad request: invalid"
    )
    from_page = classify(page)
    assert from_page is not None and from_page.category == "test_data"
    plain = classify(facts("AssertionError", "assert 'Sign in' == 'Log in'"))
    assert plain is not None and plain.category == "assertion_defect"


@pytest.mark.whitebox
def test_an_assertion_is_a_defect_even_when_its_message_mentions_a_locator() -> None:
    verdict = classify(facts("AssertionError", "no such element in the order table"))
    assert verdict is not None and verdict.category == "assertion_defect"


@pytest.mark.whitebox
def test_the_locator_name_and_page_appear_in_the_explanation() -> None:
    verdict = classify(
        facts("LookupError", "no locator strategy matched for login_submit on page login")
    )
    assert verdict is not None
    assert "login_submit" in verdict.cause and "login" in verdict.cause


@pytest.mark.whitebox
def test_a_failure_repeated_on_every_attempt_is_more_certain_than_a_single_one() -> None:
    once = classify(facts("AssertionError", "wrong total"))
    repeated = classify(facts("AssertionError", "wrong total", attempts=3))
    assert once is not None and repeated is not None
    assert repeated.confidence > once.confidence


@pytest.mark.whitebox
def test_a_timeout_that_repeats_is_still_called_flaky_with_more_confidence() -> None:
    once = classify(facts("TimeoutError", "Timeout 30000ms exceeded."))
    repeated = classify(facts("TimeoutError", "Timeout 30000ms exceeded.", attempts=2))
    assert once is not None and repeated is not None
    assert repeated.category == "timing_flaky" and repeated.confidence > once.confidence


@pytest.mark.whitebox
def test_healing_history_is_mentioned_in_the_explanation() -> None:
    verdict = classify(
        facts(
            "LookupError",
            "no locator strategy matched for login_submit on page login",
            healing_outcomes=("no_candidate", "no_candidate"),
        )
    )
    assert verdict is not None
    assert "self-healing" in verdict.cause.lower() and "no_candidate" in verdict.cause


@pytest.mark.whitebox
def test_a_healed_locator_that_did_not_fix_the_test_is_called_out() -> None:
    verdict = classify(
        facts(
            "AssertionError",
            "assert 'Thank you' in page",
            healing_outcomes=("proposed",),
        )
    )
    assert verdict is not None
    assert verdict.category == "assertion_defect"
    assert "healed locator" in verdict.cause.lower()


@pytest.mark.whitebox
def test_matching_ignores_case_and_looks_at_the_log_when_the_short_text_is_empty() -> None:
    verdict = classify(facts("Error", "", log="E   page.goto: NET::ERR_CONNECTION_REFUSED"))
    assert verdict is not None and verdict.category == "environment"


@pytest.mark.whitebox
def test_a_browser_network_error_is_quoted_with_its_full_code() -> None:
    verdict = classify(facts("Error", "page.goto: net::ERR_CONNECTION_REFUSED at http://x/"))
    assert verdict is not None and "net::ERR_CONNECTION_REFUSED" in verdict.cause
