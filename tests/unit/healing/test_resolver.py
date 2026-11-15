"""Locator strategies resolved against a DOM snapshot, and signatures derived from locators.

Requirements: FR-16 (strategies: id, CSS, XPath, text, role, attribute), FR-23
(stored fallback locators are tried first).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.core.models import Locator, LocatorStrategy
from aitaf.healing import find_elements, parse_dom, signature_from_locator

DATA = Path(__file__).resolve().parents[3] / "data" / "dom"
DOM = parse_dom((DATA / "login_before.html").read_text(encoding="utf-8"))


def find(kind: str, value: str):  # type: ignore[no-untyped-def]
    return find_elements(DOM, LocatorStrategy(kind=kind, value=value))  # type: ignore[arg-type]


def ids(found) -> list[str]:  # type: ignore[no-untyped-def]
    return [e.attrs.get("id", e.tag) for e in found]


@pytest.mark.blackbox
def test_id_strategy() -> None:
    assert ids(find("id", "login-button")) == ["login-button"]
    assert find("id", "missing") == []


@pytest.mark.blackbox
@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        ("button[type=submit]", ["login-button"]),
        ("#login-button", ["login-button"]),
        (".btn-primary", ["login-button"]),
        ("button.btn.btn-primary", ["login-button"]),
        ("form button", ["login-button"]),
        ("input[name='email']", ["email-input"]),
        ('[type="password"]', ["password-input"]),
        ("input[type^=pass]", ["password-input"]),
        ("a[href$='/reset']", ["a"]),
        ("input[placeholder*=example]", ["email-input"]),
        ("button.missing", []),
    ],
)
def test_css_strategy(selector: str, expected: list[str]) -> None:
    assert ids(find("css", selector)) == expected


@pytest.mark.blackbox
@pytest.mark.parametrize(
    ("xpath", "expected"),
    [
        ("//button[@type='submit']", ["login-button"]),
        ('//*[@id="login-button"]', ["login-button"]),
        ("//button[text()='Sign in']", ["login-button"]),
        ("//a[contains(text(),'Forgot')]", ["a"]),
        ("//input[contains(@name,'mail')]", ["email-input"]),
        ("//input[1]", ["email-input"]),
        ("//button", ["login-button"]),
        ("//button[@type='reset']", []),
    ],
)
def test_xpath_strategy(xpath: str, expected: list[str]) -> None:
    assert ids(find("xpath", xpath)) == expected


@pytest.mark.blackbox
def test_text_strategy_matches_own_text_case_insensitively() -> None:
    assert ids(find("text", "forgot")) == ["a"]
    assert sorted(ids(find("text", "SIGN IN"))) == ["h1", "login-button"]


@pytest.mark.blackbox
def test_role_strategy_uses_implicit_and_explicit_roles() -> None:
    assert ids(find("role", "button")) == ["login-button"]
    assert len(find("role", "link")) == 3
    assert ids(find("role", "textbox")) == ["email-input", "password-input"]
    explicit = parse_dom('<div role="alert" id="x">oops</div>')
    assert ids(find_elements(explicit, LocatorStrategy(kind="role", value="alert"))) == ["x"]


@pytest.mark.blackbox
def test_attr_strategy_with_and_without_value() -> None:
    assert ids(find("attr", "name=email")) == ["email-input"]
    assert len(find("attr", "type")) == 3


@pytest.mark.whitebox
@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("css", "button:first-child"),
        ("css", "form > button"),
        ("css", "a, b"),
        ("xpath", "//form/button"),
        ("xpath", "//button[@a='1' and @b='2']"),
        ("xpath", "button"),
    ],
)
def test_unsupported_selectors_return_none_not_a_wrong_answer(kind: str, value: str) -> None:
    assert find_elements(DOM, LocatorStrategy(kind=kind, value=value)) is None  # type: ignore[arg-type]


def locator(*strategies: tuple[str, str]) -> Locator:
    primary, *rest = strategies
    return Locator(
        loc_id="p.x",
        page="p",
        name="x",
        primary=LocatorStrategy(kind=primary[0], value=primary[1]),  # type: ignore[arg-type]
        fallbacks=[LocatorStrategy(kind=k, value=v) for k, v in rest],  # type: ignore[arg-type]
        model="m",
        prompt_version="p",
    )


@pytest.mark.blackbox
def test_signature_from_locator_collects_tag_attributes_and_text() -> None:
    sig = signature_from_locator(
        locator(("id", "login-button"), ("css", "button.btn[type=submit]"), ("text", "Sign in"))
    )
    assert sig.tag == "button"
    assert sig.attrs["id"] == "login-button"
    assert sig.attrs["type"] == "submit"
    assert "btn" in sig.attrs["class"].split()
    assert sig.text == "Sign in"
    assert sig.ancestors == () and sig.neighbours == ()


@pytest.mark.whitebox
def test_signature_from_xpath_role_and_attr_strategies() -> None:
    sig = signature_from_locator(
        locator(
            ("xpath", "//input[@name='email']"),
            ("role", "textbox"),
            ("attr", "data-testid=email"),
            ("xpath", "//*[text()='Email']"),
        )
    )
    assert sig.tag == "input"
    assert sig.attrs["name"] == "email"
    assert sig.attrs["role"] == "textbox"
    assert sig.attrs["data-testid"] == "email"
    assert sig.text == "Email"


@pytest.mark.whitebox
def test_primary_strategy_wins_over_fallback_for_the_same_attribute() -> None:
    sig = signature_from_locator(locator(("id", "first"), ("css", "#second")))
    assert sig.attrs["id"] == "first"


@pytest.mark.whitebox
def test_unparseable_strategies_are_ignored_for_the_signature() -> None:
    sig = signature_from_locator(locator(("css", "a:hover > b"), ("xpath", "//a/b")))
    assert sig.tag is None and sig.attrs == {} and sig.text == ""
