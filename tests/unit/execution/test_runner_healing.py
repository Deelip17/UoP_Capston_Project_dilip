"""Healing during execution (FR-22 to FR-26 as used by the Execution Engine, FR-25).

A page object that finds no element raises ``LookupError("no locator strategy matched
for <name> on page <page>")``. The engine then asks the healer (through the
``LocatorHealer`` interface from ``core``, never by importing the healing package)
for a new locator, applies it to a **temporary copy** of the scripts, and reruns the
test there. The original scripts and the locator repository are never changed:
a permanent change needs human approval (FR-25). Real PyTest subprocesses run over a
fake browser whose DOM is a rendered page of the sample shop.
"""

from __future__ import annotations

import ast
import json
import textwrap
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aitaf.core.healing import (
    ElementSignature,
    FailureContext,
    FailureKind,
    HealResult,
    HealStatus,
)
from aitaf.core.logging import set_run_id
from aitaf.core.models import LocatorStrategy, Run, RunStatus
from aitaf.core.storage import InMemoryRepository
from aitaf.execution import ExecutionEngine, RunConfig
from aitaf.healing import BaselineSnapshots, HealingConfig, SelfHealingEngine
from aitaf.sampleapp import render_page

NOW = datetime(2026, 11, 15, 10, 0, 0, tzinfo=UTC)
SHOP_DOM = Path(__file__).resolve().parents[3] / "data" / "dom" / "shop"

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


def config(root: Path, tmp_path: Path, **extra: object) -> RunConfig:
    base: dict[str, object] = {
        "scripts_dir": root,
        "base_url": "http://127.0.0.1:8765",
        "allowed_hosts": ["127.0.0.1"],
        "evidence_dir": tmp_path / "evidence",
        "run_timeout_s": 120,
        "healing": True,
    }
    return RunConfig(**{**base, **extra})  # type: ignore[arg-type]


class StubHealer:
    """Records the contexts it receives and returns a fixed result."""

    def __init__(self, result: HealResult) -> None:
        self.result = result
        self.calls: list[FailureContext] = []

    def heal(self, ctx: FailureContext) -> HealResult:
        self.calls.append(ctx)
        return self.result


HEALED_TO_NEW_ID = HealResult(
    HealStatus.HEALED,
    FailureKind.LOCATOR,
    strategy=LocatorStrategy(kind="id", value="signin-btn"),
    confidence=0.9,
)
ID_MUTATED_DOM = render_page("login", ["M-login_submit-id"])
BASELINE = BaselineSnapshots(SHOP_DOM).signature_for


@pytest.fixture
def repo() -> Iterator[InMemoryRepository]:
    repository = InMemoryRepository()
    repository.create_run(
        Run(
            run_id="run-1",
            started_at=NOW,
            status=RunStatus.RUNNING,
            provider="mock",
            environment="test",
        )
    )
    set_run_id("run-1")
    yield repository
    set_run_id("")


def locators_of(path: Path) -> dict[str, dict[str, object]]:
    text = (path / "locators" / "login_locators.py").read_text(encoding="utf-8")
    return ast.literal_eval(text.split("=", 1)[1].strip())  # type: ignore[no-any-return]


# --------------------------------------------------------------------- real healer


@pytest.mark.blackbox
def test_a_broken_locator_is_healed_and_the_test_passes_on_rerun(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    engine = ExecutionEngine(repo, healer=SelfHealingEngine(repo), baseline=BASELINE)
    summary = engine.execute(config(root, tmp_path))
    (result,) = repo.list_results("run-1")
    assert result.status == "passed" and result.attempts == 2
    assert (summary.heal_attempts, summary.healed) == (1, 1)
    assert "healed" in result.log and "login.login_submit" in result.log
    events = repo.list_healing_events("run-1")
    # The fallback rung found nothing (recorded), then similarity proposed one locator.
    assert [(e.strategy_used, e.outcome) for e in events] == [
        ("fallback", "no_candidate"),
        ("similarity", "proposed"),
    ]
    proposed = events[-1]
    assert proposed.validated and not proposed.approved


@pytest.mark.blackbox
def test_the_original_scripts_are_never_changed_only_a_temporary_copy(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    """FR-25: a permanent locator change needs human approval."""
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    ExecutionEngine(repo, healer=SelfHealingEngine(repo), baseline=BASELINE).execute(
        config(root, tmp_path)
    )
    assert locators_of(root)["login_submit"]["primary"] == ("id", "login-button")
    healed = locators_of(tmp_path / "evidence" / "healed_scripts")["login_submit"]
    assert healed["primary"] != ("id", "login-button")
    assert ("id", "login-button") in healed["fallbacks"]  # type: ignore[operator]


@pytest.mark.blackbox
def test_without_healing_the_test_stays_failed(repo: InMemoryRepository, tmp_path: Path) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    ExecutionEngine(repo, healer=SelfHealingEngine(repo), baseline=BASELINE).execute(
        config(root, tmp_path, healing=False)
    )
    (result,) = repo.list_results("run-1")
    assert result.status == "failed" and result.attempts == 1
    assert repo.list_healing_events("run-1") == []


@pytest.mark.blackbox
def test_an_engine_without_a_healer_never_heals(repo: InMemoryRepository, tmp_path: Path) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    summary = ExecutionEngine(repo).execute(config(root, tmp_path))
    assert summary.failed == 1 and summary.heal_attempts == 0


@pytest.mark.blackbox
def test_an_element_that_is_really_gone_is_not_healed(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    """The page has no similar element: the step must keep failing, not be forced to pass."""
    root = project(tmp_path, {"test_login": LOGIN_TEST}, render_page("products"))
    summary = ExecutionEngine(repo, healer=SelfHealingEngine(repo), baseline=BASELINE).execute(
        config(root, tmp_path)
    )
    (result,) = repo.list_results("run-1")
    assert result.status == "failed" and result.attempts == 1
    assert (summary.heal_attempts, summary.healed) == (1, 0)
    assert all(e.outcome != "proposed" for e in repo.list_healing_events("run-1"))


@pytest.mark.blackbox
def test_without_a_baseline_snapshot_a_changed_id_cannot_be_healed(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    """Similarity needs the original element's signature; the locator text alone is too little."""
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    summary = ExecutionEngine(repo, healer=SelfHealingEngine(repo)).execute(config(root, tmp_path))
    (result,) = repo.list_results("run-1")
    assert result.status == "failed" and result.attempts == 1
    assert (summary.heal_attempts, summary.healed) == (1, 0)
    assert {e.outcome for e in repo.list_healing_events("run-1")} == {"no_candidate"}


@pytest.mark.whitebox
def test_the_healers_attempt_limit_is_respected(repo: InMemoryRepository, tmp_path: Path) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    healer = SelfHealingEngine(repo, HealingConfig(max_attempts_per_run=0))
    ExecutionEngine(repo, healer=healer, baseline=BASELINE).execute(config(root, tmp_path))
    (result,) = repo.list_results("run-1")
    assert result.status == "failed" and result.attempts == 1
    assert repo.list_healing_events("run-1") == []


# ---------------------------------------------------------------------- stub healer


@pytest.mark.whitebox
def test_the_healer_receives_the_failing_step_the_locator_and_the_dom(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    healer = StubHealer(HEALED_TO_NEW_ID)
    ExecutionEngine(repo, healer=healer).execute(config(root, tmp_path))
    (ctx,) = healer.calls
    assert ctx.step_ref.endswith("test_login#login.login_submit")
    assert ctx.locator.loc_id == "login.login_submit"
    assert ctx.locator.primary == LocatorStrategy(kind="id", value="login-button")
    assert ctx.error_type == "LookupError"
    assert "no locator strategy matched for login_submit" in ctx.error_message
    assert "signin-btn" in ctx.dom_html
    assert ctx.baseline is None


@pytest.mark.whitebox
def test_a_baseline_signature_is_passed_to_the_healer_when_available(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    healer = StubHealer(HEALED_TO_NEW_ID)
    baseline = BaselineSnapshots(SHOP_DOM)
    ExecutionEngine(repo, healer=healer, baseline=baseline.signature_for).execute(
        config(root, tmp_path)
    )
    signature = healer.calls[0].baseline
    assert isinstance(signature, ElementSignature)
    assert signature.text == "Log in" and signature.tag == "button"


@pytest.mark.whitebox
def test_assertion_failures_and_unknown_locators_never_reach_the_healer(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_defect": DEFECT_TEST, "test_ghost": GHOST_TEST}, ID_MUTATED_DOM)
    healer = StubHealer(HEALED_TO_NEW_ID)
    summary = ExecutionEngine(repo, healer=healer).execute(config(root, tmp_path))
    assert healer.calls == []
    assert summary.failed == 2 and summary.heal_attempts == 0


@pytest.mark.whitebox
def test_a_heal_that_does_not_fix_the_step_stops_after_the_pass_limit(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    useless = HealResult(
        HealStatus.HEALED,
        FailureKind.LOCATOR,
        strategy=LocatorStrategy(kind="id", value="still-wrong"),
    )
    healer = StubHealer(useless)
    summary = ExecutionEngine(repo, healer=healer).execute(
        config(root, tmp_path, max_heal_passes=2)
    )
    (result,) = repo.list_results("run-1")
    assert result.status == "failed" and result.attempts == 3
    assert len(healer.calls) == 2 and summary.healed == 0


@pytest.mark.whitebox
def test_a_not_healed_answer_ends_the_attempt_without_a_rerun(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    healer = StubHealer(
        HealResult(HealStatus.NOT_HEALED, FailureKind.LOCATOR, reason="no candidate")
    )
    ExecutionEngine(repo, healer=healer).execute(config(root, tmp_path))
    (result,) = repo.list_results("run-1")
    assert result.status == "failed" and result.attempts == 1 and len(healer.calls) == 1


@pytest.mark.whitebox
def test_retries_still_apply_to_failures_that_are_not_locator_problems(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_defect": DEFECT_TEST}, ID_MUTATED_DOM)
    ExecutionEngine(repo, healer=StubHealer(HEALED_TO_NEW_ID)).execute(
        config(root, tmp_path, retries=1)
    )
    (result,) = repo.list_results("run-1")
    assert result.attempts == 2


@pytest.mark.whitebox
def test_the_summary_reports_the_healing_success_rate(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    summary = ExecutionEngine(repo, healer=SelfHealingEngine(repo), baseline=BASELINE).execute(
        config(root, tmp_path)
    )
    assert summary.healing_success_rate == 1.0
    empty = ExecutionEngine(repo).execute(config(root, tmp_path, healing=False))
    assert empty.healing_success_rate is None


@pytest.mark.whitebox
def test_an_unreadable_locator_file_skips_healing_instead_of_crashing(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_login": LOGIN_TEST}, ID_MUTATED_DOM)
    stub = StubHealer(HEALED_TO_NEW_ID)
    engine = ExecutionEngine(repo, healer=stub)
    first = engine.execute(config(root, tmp_path / "a"))
    assert first.healed == 1
    # A locator module that is not a plain dictionary cannot be parsed safely.
    (root / "locators" / "login_locators.py").write_text(
        'LOCATORS = {"login_submit": {"primary": tuple(["id", "login-button"]),'
        ' "fallbacks": []}}\n',
        encoding="utf-8",
    )
    again = ExecutionEngine(repo, healer=StubHealer(HEALED_TO_NEW_ID)).execute(
        config(root, tmp_path / "b")
    )
    assert again.heal_attempts == 0


@pytest.mark.whitebox
def test_two_tests_with_the_same_broken_locator_cost_one_healing_request(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(
        tmp_path, {"test_login": LOGIN_TEST, "test_login_again": LOGIN_TEST}, ID_MUTATED_DOM
    )
    healer = StubHealer(HEALED_TO_NEW_ID)
    summary = ExecutionEngine(repo, healer=healer).execute(config(root, tmp_path))
    assert len(healer.calls) == 1 and summary.heal_attempts == 1
    assert summary.passed == 2 and summary.healed == 2
