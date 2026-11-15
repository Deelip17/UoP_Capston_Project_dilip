"""Fixtures for the generated Playwright tests."""

import pytest
from playwright.sync_api import sync_playwright


def pytest_addoption(parser):
    parser.addoption("--base-url", default='http://localhost:8000', help="base URL of the system under test")


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
