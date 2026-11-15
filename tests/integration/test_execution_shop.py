"""Real-browser run of generated-style scripts against the local sample shop.

Requirements: FR-17 (execute through PyTest on Playwright), FR-18 (screenshot on
failure), FR-19 (results stored), FR-21 (browser blocked from non-listed hosts),
NFR-11. Needs Chromium (``playwright install chromium``); skipped when it is not
available. Excluded from the default run (marker ``integration``); CI runs it in
``integration.yml``.
"""

from __future__ import annotations

import textwrap
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aitaf.core.logging import set_run_id
from aitaf.core.models import Locator, LocatorStrategy, Run, RunStatus
from aitaf.core.storage import InMemoryRepository
from aitaf.execution import ExecutionEngine, RunConfig
from aitaf.sampleapp import ELEMENTS, ShopServer
from aitaf.sampleapp.server import DEMO_PASSWORD, DEMO_USER
from aitaf.scriptgen import templates

pytestmark = [pytest.mark.integration, pytest.mark.blackbox]


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            playwright.chromium.launch(headless=True).close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def browser_ready() -> None:
    if not _chromium_available():
        pytest.skip("Chromium is not installed (playwright install chromium)")


@pytest.fixture
def repo() -> Iterator[InMemoryRepository]:
    repository = InMemoryRepository()
    repository.create_run(
        Run(
            run_id="run-1",
            started_at=datetime.now(UTC),
            status=RunStatus.RUNNING,
            provider="mock",
            environment="test",
        )
    )
    set_run_id("run-1")
    yield repository
    set_run_id("")


def write_project(
    root: Path,
    base_url: str,
    guard_test: bool = True,
    primary_kinds: dict[str, str] | None = None,
    fallbacks: bool = True,
) -> Path:
    for folder in ("tests", "locators", "pages"):
        (root / folder).mkdir(parents=True)
    (root / "locators" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pages" / "__init__.py").write_text("", encoding="utf-8")
    kinds = primary_kinds or {}
    locators = []
    for e in ELEMENTS.values():
        primary = e.locator(kinds.get(e.name, "id"))
        locators.append(
            Locator(
                loc_id=f"shop.{e.name}",
                page="shop",
                name=e.name,
                primary=LocatorStrategy(kind=primary.kind, value=primary.value),  # type: ignore[arg-type]
                fallbacks=(
                    [LocatorStrategy(kind="css", value=f"{e.tag}.{e.css_class}")]
                    if fallbacks
                    else []
                ),
                model="test",
                prompt_version="n/a",
            )
        )
    (root / "locators" / "shop_locators.py").write_text(
        templates.render_locators("shop", locators), encoding="utf-8"
    )
    (root / "pages" / "shop_page.py").write_text(
        templates.render_page_object("playwright", "shop"), encoding="utf-8"
    )
    (root / "conftest.py").write_text(
        templates.render_conftest("playwright", base_url), encoding="utf-8"
    )
    journey = f"""
        from pages.shop_page import ShopPage


        def test_shop_journey(page, base_url):
            screen = ShopPage(page, base_url)
            screen.open('/')
            screen.type('username', {DEMO_USER!r})
            screen.type('password', {DEMO_PASSWORD!r})
            screen.click('login_submit')
            screen.assert_visible('add_backpack')
            screen.click('add_backpack')
            screen.click('cart_link')
            screen.assert_visible('remove_item')
            screen.click('checkout_button')
            screen.type('ship_name', 'Test Customer')
            screen.click('place_order')
            screen.assert_text('confirmation', 'Thank you for your order')


        def test_wrong_expected_text(page, base_url):
            screen = ShopPage(page, base_url)
            screen.open('/')
            screen.assert_text('login_submit', 'Sign in')

    """
    guard = """

        def test_navigation_to_an_unlisted_host_is_blocked(page, base_url):
            import pytest
            other = base_url.replace('127.0.0.1', 'localhost')
            with pytest.raises(Exception):
                page.goto(other + '/')
    """
    source = textwrap.dedent(journey) + (textwrap.dedent(guard) if guard_test else "")
    (root / "tests" / "test_shop.py").write_text(source, encoding="utf-8")
    return root


def test_real_browser_run_stores_results_and_failure_evidence(
    browser_ready: None, repo: InMemoryRepository, tmp_path: Path
) -> None:
    with ShopServer() as shop:
        root = write_project(tmp_path / "scripts", shop.url)
        config = RunConfig(
            scripts_dir=root,
            base_url=shop.url,
            allowed_hosts=["127.0.0.1"],
            evidence_dir=tmp_path / "evidence",
            timeout_ms=15_000,
            run_timeout_s=240,
            checkpoints=True,
        )
        ExecutionEngine(repo).execute(config)
    stored = {r.tc_id: r for r in repo.list_results("run-1")}
    statuses = {tc: r.status for tc, r in stored.items()}
    assert statuses == {
        "SHOP-JOURNEY": "passed",
        "WRONG-EXPECTED-TEXT": "failed",
        "NAVIGATION-TO-AN-UNLISTED-HOST-IS-BLOCKED": "passed",
    }, {tc: r.log[-300:] for tc, r in stored.items()}
    failed = stored["WRONG-EXPECTED-TEXT"]
    shot = (tmp_path / "evidence" / failed.screenshot).read_bytes()
    assert shot.startswith(b"\x89PNG") and len(shot) > 2_000
    assert "login-button" in (tmp_path / "evidence" / failed.dom_snapshot).read_text(
        encoding="utf-8"
    )
    assert (tmp_path / "evidence" / stored["SHOP-JOURNEY"].screenshot).exists()


HEAL_CASES = [
    ("M-login_submit-id", "id"),
    ("M-login_submit-class", "css"),
    ("M-login_submit-xpath", "xpath"),
    ("M-login_submit-text", "text"),
]


@pytest.mark.parametrize(("mutation", "kind"), HEAL_CASES, ids=[m for m, _ in HEAL_CASES])
def test_a_mutated_locator_is_healed_in_a_real_browser(
    browser_ready: None, repo: InMemoryRepository, tmp_path: Path, mutation: str, kind: str
) -> None:
    """The login button's locator is broken by one mutation; the journey must still pass."""
    from aitaf.healing import BaselineSnapshots, SelfHealingEngine

    baseline = BaselineSnapshots(Path(__file__).resolve().parents[2] / "data" / "dom" / "shop")
    with ShopServer(mutations=[mutation]) as shop:
        root = write_project(
            tmp_path / "scripts",
            shop.url,
            guard_test=False,
            primary_kinds={"login_submit": kind},
            fallbacks=False,
        )
        config = RunConfig(
            scripts_dir=root,
            base_url=shop.url,
            allowed_hosts=["127.0.0.1"],
            evidence_dir=tmp_path / "evidence",
            timeout_ms=15_000,
            run_timeout_s=240,
            healing=True,
        )
        engine = ExecutionEngine(
            repo, healer=SelfHealingEngine(repo), baseline=baseline.signature_for
        )
        summary = engine.execute(config)
    results = {r.tc_id: r for r in repo.list_results("run-1")}
    journey = results["SHOP-JOURNEY"]
    assert summary.heal_attempts >= 1
    assert journey.status == "passed" and journey.attempts == 2, journey.log[-400:]
    proposed = [e for e in repo.list_healing_events("run-1") if e.outcome == "proposed"]
    assert len(proposed) == 1 and not proposed[0].approved
    assert proposed[0].old_strategy.kind == kind
