"""Template rendering of scripts, page objects and the locator repository (FR-12 to FR-14).

Driver adapters (Playwright, Selenium) differ only in the page-object and
``conftest.py`` templates. Test scripts reference locators by name through the
page object; the selectors live in exactly one repository file per page. The
page object tries the primary strategy first and then each fallback in order
(FR-16), which is the first rung of the self-healing ladder.
"""

from __future__ import annotations

import re
from typing import Literal

from aitaf.core.models import Locator, TestCase
from aitaf.scriptgen.plan import PlanSchema

Framework = Literal["playwright", "selenium"]

_PLAYWRIGHT_PAGE = '''"""Page object for '__PAGE__' (generated; locators are in the repository)."""

from __LOCATORS_MODULE__ import LOCATORS


def _selector(strategy, value):
    if strategy == "id":
        return "#" + value
    if strategy == "css":
        return value
    if strategy == "xpath":
        return "xpath=" + value
    if strategy == "text":
        return "text=" + value
    if strategy == "role":
        return "role=" + value
    name, _, expected = value.partition("=")
    return "[" + name + '="' + expected + '"]'


class __CLASS__:
    def __init__(self, page, base_url):
        self._page = page
        self._base_url = base_url

    def open(self, path):
        self._page.goto(self._base_url + path)

    def _find(self, name):
        entry = LOCATORS[name]
        for strategy, value in [entry["primary"], *entry["fallbacks"]]:
            candidate = self._page.locator(_selector(strategy, value))
            if candidate.count() > 0:
                return candidate.first
        raise AssertionError("no locator strategy matched for " + name)

    def click(self, name):
        self._find(name).click()

    def type(self, name, value):
        self._find(name).fill(value)

    def select(self, name, value):
        self._find(name).select_option(value)

    def assert_text(self, name, expected):
        assert expected in self._find(name).inner_text()

    def assert_visible(self, name):
        assert self._find(name).is_visible()
'''

_SELENIUM_PAGE = '''"""Page object for '__PAGE__' (generated; locators are in the repository)."""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from __LOCATORS_MODULE__ import LOCATORS


def _by(strategy, value):
    if strategy == "id":
        return By.ID, value
    if strategy == "css":
        return By.CSS_SELECTOR, value
    if strategy == "xpath":
        return By.XPATH, value
    if strategy == "text":
        return By.XPATH, '//*[contains(text(), "' + value + '")]'
    if strategy == "role":
        return By.CSS_SELECTOR, '[role="' + value + '"]'
    name, _, expected = value.partition("=")
    return By.CSS_SELECTOR, "[" + name + '="' + expected + '"]'


class __CLASS__:
    def __init__(self, driver, base_url):
        self._driver = driver
        self._base_url = base_url

    def open(self, path):
        self._driver.get(self._base_url + path)

    def _find(self, name):
        entry = LOCATORS[name]
        for strategy, value in [entry["primary"], *entry["fallbacks"]]:
            by, selector = _by(strategy, value)
            elements = self._driver.find_elements(by, selector)
            if elements:
                return elements[0]
        raise AssertionError("no locator strategy matched for " + name)

    def click(self, name):
        self._find(name).click()

    def type(self, name, value):
        self._find(name).send_keys(value)

    def select(self, name, value):
        Select(self._find(name)).select_by_visible_text(value)

    def assert_text(self, name, expected):
        assert expected in self._find(name).text

    def assert_visible(self, name):
        assert self._find(name).is_displayed()
'''

_PLAYWRIGHT_CONFTEST = '''"""Fixtures for the generated Playwright tests."""

import pytest
from playwright.sync_api import sync_playwright


def pytest_addoption(parser):
    parser.addoption("--base-url", default=__BASE_URL__, help="base URL of the system under test")


@pytest.fixture
def base_url(request):
    return request.config.getoption("--base-url")


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()
'''

_SELENIUM_CONFTEST = '''"""Fixtures for the generated Selenium tests."""

import pytest
from selenium import webdriver


def pytest_addoption(parser):
    parser.addoption("--base-url", default=__BASE_URL__, help="base URL of the system under test")


@pytest.fixture
def base_url(request):
    return request.config.getoption("--base-url")


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    browser = webdriver.Chrome(options=options)
    yield browser
    browser.quit()
'''


def identifier(text: str) -> str:
    """Lowercase identifier made of letters, digits and single underscores."""
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower() or "case"


def class_name(page: str) -> str:
    return "".join(part.capitalize() for part in page.split("_")) + "Page"


def locators_module(page: str) -> str:
    return f"locators.{page}_locators"


def pages_module(page: str) -> str:
    return f"pages.{page}_page"


def render_locators(page: str, locators: list[Locator]) -> str:
    lines = [
        f'"""Locator repository for the {page!r} page. Generated; selectors live only here."""',
        "",
        "LOCATORS = {",
    ]
    for loc in locators:
        fallbacks = ", ".join(f"({f.kind!r}, {f.value!r})" for f in loc.fallbacks)
        lines += [
            f"    {loc.name!r}: {{",
            f'        "primary": ({loc.primary.kind!r}, {loc.primary.value!r}),',
            f'        "fallbacks": [{fallbacks}],',
            "    },",
        ]
    lines += ["}", ""]
    return "\n".join(lines)


def render_page_object(framework: Framework, page: str) -> str:
    template = _PLAYWRIGHT_PAGE if framework == "playwright" else _SELENIUM_PAGE
    return (
        template.replace("__PAGE__", page)
        .replace("__CLASS__", class_name(page))
        .replace("__LOCATORS_MODULE__", locators_module(page))
    )


def render_conftest(framework: Framework, base_url: str) -> str:
    template = _PLAYWRIGHT_CONFTEST if framework == "playwright" else _SELENIUM_CONFTEST
    return template.replace("__BASE_URL__", repr(base_url))


def render_test(
    framework: Framework, case: TestCase, plan: PlanSchema, ident: str, model: str, version: str
) -> str:
    fixture = "page" if framework == "playwright" else "driver"
    title = " ".join(case.title.split())
    lines = [
        f"# {case.tc_id}: {title}".replace("\n", " "),
        f"# AI-generated by {model} (prompt {version}); review before relying on it.",
        f"from {pages_module(plan.page)} import {class_name(plan.page)}",
        "",
        "",
        f"def test_{ident}({fixture}, base_url):",
        f"    screen = {class_name(plan.page)}({fixture}, base_url)",
    ]
    for step in plan.steps:
        args = [repr(a) for a in (step.target, step.value) if a is not None]
        lines.append(f"    screen.{step.action}({', '.join(args)})")
    lines.append("")
    return "\n".join(lines)
