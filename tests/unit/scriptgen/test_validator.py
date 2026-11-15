"""Static validation of generated scripts (AST allow-list).

Requirements: FR-15 (syntax, forbidden imports and calls, no hard-coded secrets,
rejected with a reason), NFR-11 (least privilege: no shell, no network outside the
driver and allow-listed hosts, no writes outside permitted directories).
"""

from __future__ import annotations

import pytest

from aitaf.core.errors import PolicyError
from aitaf.scriptgen import assert_valid, validate_script

HOSTS = frozenset({"localhost", "127.0.0.1"})

BENIGN = """
import pytest
from playwright.sync_api import sync_playwright
from locators.home_locators import LOCATORS
from pages.home_page import HomePage


def test_example(page, base_url):
    home = HomePage(page, base_url)
    home.open("/")
    home.type("email", "demo.user@example.test")
    home.click("submit_button")
    assert "ok" in "ok"
"""

FORBIDDEN = {
    "os-import": ("import os\nos.system('dir')\n", "import"),
    "subprocess-import": ("import subprocess\n", "import"),
    "socket-import": ("from socket import socket\n", "import"),
    "requests-import": ("import requests\nrequests.get('http://localhost/')\n", "import"),
    "relative-import": ("from . import secrets\n", "relative"),
    "eval-call": ("x = eval('1+1')\n", "eval"),
    "exec-call": ("exec('print(1)')\n", "exec"),
    "open-call": ("open('out.txt', 'w').write('x')\n", "open"),
    "dunder-import": ("m = __import__('os')\n", "__import__"),
    "getattr-call": ("getattr(page, 'x')\n", "getattr"),
    "dunder-attribute": ("x = ().__class__.__bases__\n", "dunder"),
    "evaluate-js": ("def t(page):\n    page.evaluate('fetch(1)')\n", "evaluate"),
    "execute-script": ("def t(driver):\n    driver.execute_script('1')\n", "execute_script"),
    "write-text": ("def t(path):\n    path.write_text('x')\n", "write_text"),
    "disallowed-host": ("URL = 'http://evil.example/steal'\n", "evil.example"),
    "file-scheme": ("URL = 'file:///etc/passwd'\n", "file"),
    "hardcoded-secret-name": ("password = 'Hunter2Hunter2'\n", "secret"),
    "hardcoded-secret-keyword": ("def t(page):\n    page.fill('#p', password='x')\n", "secret"),
    "api-key-literal": ("KEY = 'sk-' + 'abc'\nBAD = 'sk-abcdEFGH12345678xyz'\n", "secret"),
    "real-looking-email": ("EMAIL = 'john.smith@gmail.com'\n", "personal"),
    "syntax-error": ("def broken(:\n", "syntax"),
}


@pytest.mark.blackbox
def test_benign_generated_script_passes() -> None:
    assert validate_script(BENIGN, HOSTS) == []


@pytest.mark.blackbox
@pytest.mark.parametrize("name", sorted(FORBIDDEN))
def test_forbidden_construct_is_rejected_with_a_reason(name: str) -> None:
    source, hint = FORBIDDEN[name]
    problems = validate_script(source, HOSTS)
    assert problems, name
    assert any(hint.lower() in problem.lower() for problem in problems), problems


@pytest.mark.blackbox
def test_assert_valid_raises_policy_error_listing_every_reason() -> None:
    with pytest.raises(PolicyError) as info:
        assert_valid("import os\nx = eval('1')\n", HOSTS, name="test_x.py")
    message = str(info.value)
    assert "test_x.py" in message and "import" in message and "eval" in message


@pytest.mark.blackbox
def test_allowed_host_url_passes() -> None:
    assert validate_script("BASE = 'http://localhost:8000/login'\n", HOSTS) == []


@pytest.mark.whitebox
def test_reasons_include_line_numbers() -> None:
    problems = validate_script("x = 1\ny = eval('2')\n", HOSTS)
    assert problems[0].startswith("line 2:")


@pytest.mark.whitebox
def test_reserved_domain_emails_are_not_treated_as_personal_data() -> None:
    assert validate_script("EMAIL = 'a@example.test'\nB = 'c@example.com'\n", HOSTS) == []


@pytest.mark.whitebox
def test_allowed_imports_include_driver_and_generated_packages() -> None:
    source = (
        "from __future__ import annotations\n"
        "import pytest\n"
        "from selenium import webdriver\n"
        "from selenium.webdriver.common.by import By\n"
        "from selenium.webdriver.support.ui import Select\n"
        "from locators.x_locators import LOCATORS\n"
        "from pages.x_page import XPage\n"
    )
    assert validate_script(source, HOSTS) == []


@pytest.mark.whitebox
def test_several_violations_are_all_reported() -> None:
    problems = validate_script("import os\nimport subprocess\neval('1')\n", HOSTS)
    assert len(problems) == 3
