"""Fake-browser project used by several test directories (FR-17 to FR-28).

A generated-style project (conftest, page object, locator file, tests, manifest) whose
"browser" serves a rendered page of the sample shop from ``dom.html``. Real PyTest runs
it in a subprocess, so no browser is needed.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from aitaf.sampleapp import render_page

SHOP_DOM = Path(__file__).resolve().parents[2] / "data" / "dom" / "shop"

CONFTEST = """
import pytest


def pytest_addoption(parser):
    parser.addoption("--base-url", default="http://127.0.0.1:1")


class FakePage:
    def __init__(self):
        self._dom = open("dom.html", encoding="utf-8").read()

    def screenshot(self, path):
        with open(path, "wb") as handle:
            handle.write(b"\\x89PNG fake")

    def content(self):
        return self._dom


@pytest.fixture
def base_url(request):
    return request.config.getoption("--base-url")


@pytest.fixture
def page():
    yield FakePage()
"""

PAGE_OBJECT = """
from aitaf.core.models import LocatorStrategy
from aitaf.healing import find_elements, parse_dom
from locators.login_locators import LOCATORS


class LoginPage:
    def __init__(self, page, base_url):
        self._page = page

    def click(self, name):
        dom = parse_dom(self._page.content())
        entry = LOCATORS[name]
        for kind, value in [entry["primary"], *entry["fallbacks"]]:
            if find_elements(dom, LocatorStrategy(kind=kind, value=value)):
                return
        raise LookupError("no locator strategy matched for " + name + " on page login")
"""

LOCATORS = 'LOCATORS = {"login_submit": {"primary": ("id", "login-button"), "fallbacks": []}}\n'

LOGIN_TEST = (
    "from pages.login_page import LoginPage\n\n\n"
    "def test_login(page, base_url):\n    LoginPage(page, base_url).click('login_submit')\n"
)
DEFECT_TEST = "def test_defect(page):\n    assert 1 == 2, 'wrong total'\n"
GHOST_TEST = (
    "def test_ghost(page):\n"
    "    raise LookupError('no locator strategy matched for ghost on page nowhere')\n"
)


def project(tmp_path: Path, tests: dict[str, str], dom: str) -> Path:
    root = tmp_path / "scripts"
    for folder in ("tests", "locators", "pages"):
        (root / folder).mkdir(parents=True)
    (root / "locators" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pages" / "__init__.py").write_text("", encoding="utf-8")
    (root / "locators" / "login_locators.py").write_text(LOCATORS, encoding="utf-8")
    (root / "pages" / "login_page.py").write_text(PAGE_OBJECT, encoding="utf-8")
    (root / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    (root / "dom.html").write_text(dom, encoding="utf-8")
    entries = []
    for name, source in tests.items():
        (root / "tests" / f"{name}.py").write_text(textwrap.dedent(source), encoding="utf-8")
        entries.append({"tc_id": name.upper().replace("_", "-"), "path": f"tests/{name}.py"})
    (root / "manifest.json").write_text(json.dumps(entries), encoding="utf-8")
    return root


ID_MUTATED_DOM = render_page("login", ["M-login_submit-id"])
