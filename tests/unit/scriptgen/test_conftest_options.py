"""Generated conftest files accept the Execution Engine's options (FR-17, FR-20, FR-21, NFR-11).

The options are read with ``getoption(name, default=...)`` so a generated suite still
runs with plain ``pytest``. The conftest must pass the same static validation as any
generated file: no ``os``, no ``urllib``.
"""

from __future__ import annotations

import pytest

from aitaf.scriptgen import templates
from aitaf.scriptgen.validator import validate_script

OPTIONS = {
    "playwright": ("--aitaf-headed", "--aitaf-timeout-ms", "--aitaf-allowed-hosts"),
    # Selenium cannot intercept requests, so only the base-URL check protects it (README).
    "selenium": ("--aitaf-headed", "--aitaf-timeout-ms"),
}


@pytest.mark.blackbox
@pytest.mark.parametrize("framework", ["playwright", "selenium"])
def test_conftest_reads_the_engine_options_with_defaults(framework: str) -> None:
    source = templates.render_conftest(framework, "http://localhost:8000")  # type: ignore[arg-type]
    for option in OPTIONS[framework]:
        assert f'"{option}"' in source
    assert "default=" in source
    assert validate_script(source, {"localhost"}) == []


@pytest.mark.whitebox
def test_playwright_conftest_blocks_requests_to_hosts_outside_the_allow_list() -> None:
    source = templates.render_conftest("playwright", "http://localhost:8000")
    assert "page.route(" in source and "route.abort()" in source


@pytest.mark.whitebox
def test_selenium_conftest_sets_a_page_load_timeout() -> None:
    source = templates.render_conftest("selenium", "http://localhost:8000")
    assert "set_page_load_timeout" in source
