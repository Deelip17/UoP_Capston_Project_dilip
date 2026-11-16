"""Fixtures for the generated Playwright tests."""

import pytest
from playwright.sync_api import sync_playwright


def pytest_addoption(parser):
    parser.addoption("--base-url", default='http://127.0.0.1:55688', help="base URL of the system under test")


@pytest.fixture
def base_url(request):
    return request.config.getoption("--base-url")


def _host(url):
    rest = url.split("://", 1)[-1]
    return rest.split("/", 1)[0].rsplit("@", 1)[-1].split(":")[0].lower()


@pytest.fixture
def page(request):
    config = request.config
    headed = config.getoption("--aitaf-headed", default=False)
    timeout = config.getoption("--aitaf-timeout-ms", default=10000)
    hosts = [h for h in config.getoption("--aitaf-allowed-hosts", default="").split(",") if h]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        page = browser.new_page()
        page.set_default_timeout(timeout)
        if hosts:

            def guard(route, request):
                url = request.url
                if url.startswith(("data:", "about:", "blob:")) or _host(url) in hosts:
                    route.continue_()
                else:
                    route.abort()

            page.route("**/*", guard)
        yield page
        browser.close()
