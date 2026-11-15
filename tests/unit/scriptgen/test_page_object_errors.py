"""A page object that finds no element raises a locator error naming the step (FR-22, FR-23).

The Self-Healing Engine can only act on a failure it recognises as a locator problem,
and an ``AssertionError`` is always treated as an application defect. So a generated
page object raises ``LookupError`` (not ``AssertionError``) when every strategy fails,
and the message names the locator and the page so a repair can be targeted.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from aitaf.core.models import Locator, LocatorStrategy
from aitaf.scriptgen import templates


class EmptyPlaywrightPage:
    def locator(self, selector: str) -> Any:
        return SimpleNamespace(count=lambda: 0)


class EmptySeleniumDriver:
    def find_elements(self, by: str, selector: str) -> list[Any]:
        return []


_NAMES = ("locators", "pages", "locators.checkout_locators", "pages.checkout_page")


@pytest.fixture
def modules() -> Iterator[None]:
    """Import generated modules freshly and leave no trace for other tests."""
    for name in _NAMES:
        sys.modules.pop(name, None)
    yield
    for name in _NAMES:
        sys.modules.pop(name, None)


def build(tmp_path: Path, framework: str) -> Any:
    for folder in ("locators", "pages"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "__init__.py").write_text("", encoding="utf-8")
    locator = Locator(
        loc_id="checkout.place_order",
        page="checkout",
        name="place_order",
        primary=LocatorStrategy(kind="id", value="place-order"),
        model="test",
        prompt_version="n/a",
    )
    (tmp_path / "locators" / "checkout_locators.py").write_text(
        templates.render_locators("checkout", [locator]), encoding="utf-8"
    )
    (tmp_path / "pages" / "checkout_page.py").write_text(
        templates.render_page_object(framework, "checkout"),  # type: ignore[arg-type]
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        return importlib.import_module("pages.checkout_page").CheckoutPage
    finally:
        sys.path.remove(str(tmp_path))


@pytest.mark.blackbox
@pytest.mark.parametrize("framework", ["playwright", "selenium"])
def test_a_missing_element_raises_a_lookup_error_naming_the_locator_and_page(
    tmp_path: Path, modules: None, framework: str
) -> None:
    page_class = build(tmp_path, framework)
    fake = EmptyPlaywrightPage() if framework == "playwright" else EmptySeleniumDriver()
    with pytest.raises(LookupError) as info:
        page_class(fake, "http://localhost:8000").click("place_order")
    assert str(info.value) == "no locator strategy matched for place_order on page checkout"


@pytest.mark.whitebox
@pytest.mark.parametrize("framework", ["playwright", "selenium"])
def test_the_not_found_error_is_not_an_assertion_error(
    tmp_path: Path, modules: None, framework: str
) -> None:
    page_class = build(tmp_path, framework)
    fake = EmptyPlaywrightPage() if framework == "playwright" else EmptySeleniumDriver()
    try:
        page_class(fake, "http://localhost:8000").click("place_order")
    except LookupError as exc:
        assert not isinstance(exc, AssertionError)
