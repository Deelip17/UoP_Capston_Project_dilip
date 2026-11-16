"""A corpus of real test failures for the classification evaluation (FR-27, FR-28, NFR-15).

About fifty small tests are run in real Chromium against the sample shop, each written to
fail in a different way (a missing element, a wrong expectation, an unreachable server, a
timeout, rejected input, an unexpected exception). The run is stored like any other, but
the Failure Analyzer is NOT run on it: the author reads ``failures_to_label.csv`` and
fills in ``labels.csv`` first. Only then does ``classify`` score the analyzer against
those labels (``classify_eval``); it refuses a corpus the analyzer has already seen.

Tests are numbered, not named after their cause, and the recipes carry no category, so
neither the file names nor the data tell the analyzer (or the reader) the answer.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import tempfile
import textwrap
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aitaf.core.logging import new_run_id, set_run_id
from aitaf.core.metrics import Metrics
from aitaf.core.models import Locator, LocatorStrategy, Run, RunStatus, TestResult
from aitaf.core.storage import SqliteRepository
from aitaf.evaluation.corpus_holdout import LOCATOR_FAILURES as HOLDOUT_LOCATORS
from aitaf.evaluation.corpus_holdout import RAW as HOLDOUT_RAW
from aitaf.execution import ExecutionEngine, RunConfig
from aitaf.sampleapp import ELEMENTS, ShopServer
from aitaf.scriptgen import templates

MIN_FAILURES = 40
FAILURES_FILE = "failures_to_label.csv"
LABELS_FILE = "labels.csv"
_NAME = "ship_name"

_LOCATOR_FAILURES = [
    ("login", "screen.open('/')\n    screen.type('username', 'someone@example.com')"),
    ("login", "screen.open('/')\n    screen.type('password', 'secret-word')"),
    ("login", "screen.open('/')\n    screen.click('login_submit')"),
    ("login", "screen.open('/products')\n    screen.click('add_backpack')"),
    ("login", "screen.open('/products')\n    screen.click('cart_link')"),
    ("login", "screen.open('/products')\n    screen.assert_visible('add_backpack')"),
    ("login", "screen.open('/checkout')\n    screen.type('ship_name', 'A. Customer')"),
    ("login", "screen.open('/checkout')\n    screen.click('place_order')"),
    ("login", "screen.open('/')\n    screen.assert_text('login_submit', 'Log in')"),
    ("login", "screen.open('/')\n    screen.assert_visible('username')"),
    (
        "login",
        "screen.open('/products')\n    screen.assert_text('cart_link', 'View shopping cart')",
    ),
    ("login", "screen.open('/checkout')\n    screen.assert_visible('place_order')"),
]

_RAW = [
    # expectations about page content
    "page.goto(base_url + '/')\n    assert page.inner_text('h1') == 'Sign in'",
    "page.goto(base_url + '/products')\n    assert '$40.00' in page.inner_text('body')",
    "page.goto(base_url + '/products')\n    assert page.locator('li').count() == 4",
    "page.goto(base_url + '/')\n    assert page.title() == 'Demo Shop - Home'",
    "page.goto(base_url + '/')\n    page.fill('input[name=username]', 'nobody')\n"
    "    assert page.input_value('input[name=username]') == 'someone'",
    "page.goto(base_url + '/products')\n    assert 'Desk Lamp' not in page.inner_text('body')",
    "page.goto(base_url + '/')\n    assert page.inner_text('button') == 'Sign in'",
    "page.goto(base_url + '/checkout')\n    assert page.inner_text('h1') == 'Payment'",
    "page.goto(base_url + '/products')\n    assert page.locator('button').count() == 2",
    "page.goto(base_url + '/')\n    assert page.is_visible('text=Forgot password?')",
    # servers and hosts
    "page.goto('http://127.0.0.1:1/')",
    "page.goto('http://127.0.0.1:9/')",
    "page.goto('http://localhost:9/')",
    "page.goto('http://no-such-host.invalid/')",
    "page.goto('http://example.com/')",
    "response = page.goto(base_url + '/missing')\n    assert response.status == 200",
    "page.goto('http://127.0.0.1:2/checkout')",
    "page.goto('ftp://127.0.0.1/')",
    # waiting
    "page.set_default_timeout(1)\n    page.goto(base_url + '/')\n    page.click('text=Log in')",
    "page.goto(base_url + '/')\n    page.wait_for_selector('#welcome-banner', timeout=500)",
    "page.goto(base_url + '/')\n    page.wait_for_url('**/products', timeout=500)",
    "page.goto(base_url + '/', timeout=1)",
    "page.goto(base_url + '/')\n"
    "    page.wait_for_selector('text=Loading...', state='visible', timeout=400)",
    "page.goto(base_url + '/')\n    page.click('button#slow-save', timeout=300)",
    "page.goto(base_url + '/products')\n"
    "    page.wait_for_function('document.querySelectorAll(\"li\").length === 5', timeout=400)",
    "page.goto(base_url + '/')\n    page.fill('input[name=search]', 'x', timeout=300)",
    # forms
    "page.goto(base_url + '/products')\n    page.click('text=Add Backpack to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.click('text=Place order')\n"
    "    assert 'Thank you for your order' in page.inner_text('body')",
    "page.goto(base_url + '/products')\n    page.click('text=Add Backpack to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', 'N' * 81)\n"
    "    page.click('text=Place order')\n"
    "    assert 'Thank you for your order' in page.inner_text('body')",
    "page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', '')\n"
    "    page.click('text=Place order')\n"
    "    assert 'Order placed' in page.inner_text('body')",
    "page.goto(base_url + '/products')\n    page.click('text=Add Notebook to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', 'x' * 200)\n"
    "    page.click('text=Place order')\n    assert page.is_visible('text=Thank you')",
    "page.goto(base_url + '/products')\n    page.click('text=Add Desk Lamp to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', '   ')\n"
    "    page.click('text=Place order')\n    assert 'Order confirmed' in page.inner_text('body')",
    "page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', 'z' * 90)\n"
    "    page.click('text=Place order')\n    assert page.is_visible('text=Thank you')",
    "page.goto(base_url + '/products')\n    page.click('text=Add Backpack to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', '')\n"
    "    page.click('text=Place order')\n    assert 'confirmed' in page.inner_text('body')",
    "page.goto(base_url + '/products')\n    page.click('text=Add Notebook to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', 'y' * 100)\n"
    "    page.click('text=Place order')\n"
    "    assert 'Thank you for your order' in page.inner_text('body')",
    # unexpected exceptions
    "raise RuntimeError('unexpected state')",
    "value = 1 / 0",
    "settings = {}\n    settings['missing']",
    "int('abc')",
]


@dataclass(frozen=True)
class CorpusInfo:
    """What was built: where, which run, and how many tests failed or passed."""

    folder: Path
    db: Path
    run_id: str
    failures: int
    passed: int


def _locators() -> list[Locator]:
    out = []
    for e in ELEMENTS.values():
        spec = e.locator("id")
        out.append(
            Locator(
                loc_id=f"shop.{e.name}",
                page="shop",
                name=e.name,
                primary=LocatorStrategy(kind=spec.kind, value=spec.value),  # type: ignore[arg-type]
                fallbacks=[],
                model="evaluation",
                prompt_version="n/a",
            )
        )
    return out


def corpus_sources(recipe_set: str = "dev") -> list[str]:
    """The source of every corpus test, in order (``test_case_001`` and so on)."""
    if recipe_set not in ("dev", "holdout"):
        raise ValueError("recipe_set must be 'dev' or 'holdout'")
    located, raw = (
        (_LOCATOR_FAILURES, _RAW) if recipe_set == "dev" else (HOLDOUT_LOCATORS, HOLDOUT_RAW)
    )
    sources = []
    bodies = [f"screen = ShopPage(page, base_url)\n    {body}" for _, body in located] + raw
    for number, body in enumerate(bodies, start=1):
        head = "from pages.shop_page import ShopPage\n\n\n" if "ShopPage" in body else ""
        sources.append(f"{head}def test_case_{number:03d}(page, base_url):\n    {body}\n")
    return sources


def _write_project(root: Path, base_url: str, recipe_set: str) -> list[dict[str, str]]:
    for folder in ("tests", "locators", "pages"):
        (root / folder).mkdir(parents=True)
    (root / "locators" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pages" / "__init__.py").write_text("", encoding="utf-8")
    (root / "locators" / "shop_locators.py").write_text(
        templates.render_locators("shop", _locators()), encoding="utf-8"
    )
    (root / "pages" / "shop_page.py").write_text(
        templates.render_page_object("playwright", "shop"), encoding="utf-8"
    )
    (root / "conftest.py").write_text(
        templates.render_conftest("playwright", base_url), encoding="utf-8"
    )
    manifest = []
    for number, source in enumerate(corpus_sources(recipe_set), start=1):
        path = f"tests/test_case_{number:03d}.py"
        (root / path).write_text(source, encoding="utf-8")
        manifest.append({"tc_id": f"F{number:03d}", "path": path})
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


_USER_PATH = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'<>]+")
_TEXT_SUFFIXES = frozenset({".xml", ".jsonl", ".html", ".ini", ".txt", ".log"})


def scrub(text: str) -> str:
    """Remove local user-profile paths (the corpus is committed and shared)."""
    return _USER_PATH.sub("<user>", text)


def _scrub_evidence(folder: Path) -> None:
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix in _TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            clean = scrub(text)
            if clean != text:
                path.write_text(clean, encoding="utf-8", newline="\n")


def build_corpus(folder: Path | str, timeout_ms: int = 3000, recipe_set: str = "dev") -> CorpusInfo:
    """Run the corpus tests in Chromium and write the files the author labels from."""
    out = Path(folder)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{out.name!r} is not empty; the corpus is built once")
    out.mkdir(parents=True, exist_ok=True)
    db = out / "corpus.db"
    run_id = new_run_id()
    mutations = [f"M-{name}-id" for name in ELEMENTS]
    with tempfile.TemporaryDirectory() as work, ShopServer(mutations, open_login=True) as shop:
        scripts = Path(work) / "scripts"
        scripts.mkdir()
        _write_project(scripts, shop.url, recipe_set)
        config = RunConfig(
            scripts_dir=scripts,
            base_url=shop.url,
            allowed_hosts=("127.0.0.1",),
            evidence_dir=(out / "evidence").resolve(),
            timeout_ms=timeout_ms,
            run_timeout_s=900,
        )
        started = datetime.now(UTC)
        scratch = SqliteRepository(Path(work) / "run.db")
        try:
            set_run_id(run_id)
            scratch.create_run(
                Run(
                    run_id=run_id,
                    started_at=started,
                    status=RunStatus.RUNNING,
                    provider="mock",
                    environment="evaluation-corpus",
                )
            )
            summary = ExecutionEngine(scratch, Metrics(scratch)).execute(config)
            results = scratch.list_results(run_id)
        finally:
            scratch.close()
            set_run_id("")
    _scrub_evidence(out)
    clean = [
        r.model_copy(
            update={
                "log": scrub(r.log),
                "error_text": scrub(r.error_text),
                "nodeid": scrub(r.nodeid),
            }
        )
        for r in results
    ]
    repo = SqliteRepository(db)  # the stored corpus holds scrubbed copies only
    try:
        repo.create_run(
            Run(
                run_id=run_id,
                started_at=started,
                status=RunStatus.RUNNING,
                provider="mock",
                environment="evaluation-corpus",
            )
        )
        for result in clean:
            repo.add_result(result)
        repo.finish_run(run_id, RunStatus.COMPLETED, datetime.now(UTC))
    finally:
        repo.close()
    sources = {f"F{n:03d}": s for n, s in enumerate(corpus_sources(recipe_set), start=1)}
    failed = [r for r in clean if r.status in ("failed", "error")]
    _write_label_files(out, failed, sources)
    return CorpusInfo(out, db, run_id, len(failed), summary.passed)


def _write_label_files(out: Path, failed: list[TestResult], sources: dict[str, str]) -> None:
    with (out / FAILURES_FILE).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["tc_id", "error_type", "error_text", "screenshot", "test_source"])
        for result in sorted(failed, key=lambda r: r.tc_id):
            writer.writerow(
                [
                    result.tc_id,
                    result.error_type,
                    " ".join(result.error_text.split())[:400],
                    result.screenshot or "",
                    textwrap.dedent(sources.get(result.tc_id, "")).strip().replace("\n", " ⏎ "),
                ]
            )
    with (out / LABELS_FILE).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["tc_id", "category"])
        for result in sorted(failed, key=lambda r: r.tc_id):
            writer.writerow([result.tc_id, ""])


def copy_corpus(source: Path | str, target: Path | str) -> Path:
    """A throw-away copy of the corpus database, so each scoring run starts unanalysed."""
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(source), destination)
    return destination
