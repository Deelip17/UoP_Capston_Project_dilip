"""Acceptance checks AT-FR-20 to AT-FR-39: execution, healing, analysis, reporting (ADR-046).

One check per functional requirement, written from the acceptance column of
``docs/requirements/FUNCTIONAL_REQUIREMENTS.md`` and run by the author as the customer
(self-review). They use the public command line and package interfaces, the mock provider
and no browser, so they belong to the default run. The browser-dependent checks (FR-12 and
FR-17 to FR-19) are in ``tests/system/test_acceptance_browser.py``.

The first docstring line of each test is ``AT-FR-nn: <criterion>``; a ``PARTLY:`` line names
what the check does not demonstrate. Both are read when the acceptance matrix is built.
"""

from __future__ import annotations

import csv
import os
import re
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fake_browser_project import project
from pipeline_records import EXEC, SOURCE, seeded_repo
from pipeline_records import result as stored_result
from pipeline_records import run as stored_run

from aitaf.analyzer import COMPONENT as ANALYZER_COMPONENT
from aitaf.analyzer import RequirementAnalyzer, mock_extraction_responder
from aitaf.analyzer.intake import RawRequirement
from aitaf.cli import main
from aitaf.core.errors import ExecutionError, LlmTransientError, PolicyError
from aitaf.core.healing import FailureContext, HealStatus
from aitaf.core.llm import LlmGateway, LlmRequest, LlmResponse, MockProvider
from aitaf.core.llm.util import input_hash
from aitaf.core.logging import set_run_id
from aitaf.core.masking import mask
from aitaf.core.models import Locator, LocatorStrategy, Run, RunStatus, TestResult
from aitaf.core.storage import InMemoryRepository, SqliteRepository
from aitaf.dashboard import collect, render_dashboard
from aitaf.diagnosis import FailureAnalyzer
from aitaf.evaluation import run_healing_evaluation, select_mutations
from aitaf.evaluation.summary import healing_by_kind
from aitaf.execution import ExecutionEngine, RunConfig
from aitaf.healing import (
    HealingConfig,
    SelfHealingEngine,
    approve_healing_event,
    mock_healing_responder,
    parse_dom,
    signature_of,
    update_locator_from_event,
)
from aitaf.reporting import (
    build_report,
    compute_metrics,
    render_html,
    render_markdown,
    trace_for_requirement,
    trace_for_result,
    write_report,
)
from aitaf.reporting.model import format_value

pytestmark = [pytest.mark.acceptance, pytest.mark.blackbox]

ROOT = Path(__file__).resolve().parents[2]
DOM = ROOT / "data" / "dom"
SAMPLE_PLAIN = ROOT / "data" / "requirements" / "sample_plain.txt"
NOW = datetime(2026, 11, 16, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------- helpers


@pytest.fixture
def repo() -> Iterator[InMemoryRepository]:
    repository = InMemoryRepository()
    repository.create_run(
        Run(
            run_id="run-1",
            started_at=NOW,
            status=RunStatus.RUNNING,
            provider="mock",
            environment="acceptance",
        )
    )
    set_run_id("run-1")
    yield repository
    set_run_id("")


def cli(*args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["LLM_PROVIDER"] = "mock"
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL"):
        env.pop(name, None)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, "-m", "aitaf", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def heal_args(after: str, *extra: str, db: Path) -> list[str]:
    return [
        "heal",
        "--db",
        str(db),
        "--before",
        str(DOM / "login_before.html"),
        "--after",
        str(DOM / after),
        "--primary",
        "id=login-button",
        "--fallback",
        "css=button[type=submit]",
        *extra,
    ]


def html(name: str) -> str:
    return (DOM / name).read_text(encoding="utf-8")


BEFORE = parse_dom(html("login_before.html"))
BASELINE = signature_of(BEFORE, next(e for e in BEFORE.elements if e.tag == "button"))
CSS_ONLY = (("css", "button[type=submit]"),)


def make_locator(fallbacks: tuple[tuple[str, str], ...] | None = None) -> Locator:
    chosen = (
        (("css", "button[type=submit]"), ("text", "Sign in")) if fallbacks is None else fallbacks
    )
    return Locator(
        loc_id="login.login_button",
        page="login",
        name="login_button",
        primary=LocatorStrategy(kind="id", value="login-button"),
        fallbacks=[LocatorStrategy(kind=k, value=v) for k, v in chosen],  # type: ignore[arg-type]
        model="mock-1",
        prompt_version="sg-v2",
    )


def make_context(
    page: str, locator: Locator | None = None, step: str = "TC-1:step3"
) -> FailureContext:
    return FailureContext(
        step_ref=step,
        action="click",
        locator=locator or make_locator(),
        error_type="NoSuchElementException",
        error_message="no such element",
        dom_html=html(page),
        baseline=BASELINE,
    )


class CountingProvider:
    """Mock-backed provider that counts the calls the healer makes to the model."""

    name = "mock"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, req: LlmRequest) -> LlmResponse:
        self.calls += 1
        text = mock_healing_responder(req)
        return LlmResponse(text=text, model="mock-1", tokens_in=1, tokens_out=1, mock=True)


def failure(rid: str, tc: str, status: str, error_type: str, text: str, **extra: Any) -> TestResult:
    base: dict[str, Any] = {
        "result_id": rid,
        "run_id": "run-1",
        "tc_id": tc,
        "status": status,
        "duration_ms": 10,
        "log": text,
        "nodeid": f"tests/test_{tc.lower()}.py::test_{tc.lower()}",
        "error_type": error_type,
        "error_text": text,
    }
    return TestResult(**{**base, **extra})


LOCATOR_MISS = "no locator strategy matched for login_submit on page login"
CATEGORIES = {"locator", "assertion_defect", "timing_flaky", "environment", "test_data", "unknown"}


def analysed(repo: InMemoryRepository) -> tuple[Any, list[TestResult]]:
    """Store a mixed set of results and run the Failure Analyzer without a model."""
    items = [
        failure("r1", "TC-1", "failed", "LookupError", LOCATOR_MISS),
        failure("r2", "TC-2", "failed", "LookupError", LOCATOR_MISS.replace("login", "cart")),
        failure("r3", "TC-3", "failed", "AssertionError", "wrong total", attempts=2),
        failure("r4", "TC-4", "error", "ConnectionRefusedError", "[Errno 111] Connection refused"),
        failure("r5", "TC-5", "failed", "TimeoutError", "Timeout 30000ms exceeded. run 12"),
        failure("r6", "TC-6", "failed", "TimeoutError", "Timeout 10000ms exceeded. run 99"),
        failure("r7", "TC-7", "failed", "RuntimeError", "unexpected state"),
        failure("r8", "TC-8", "passed", "", ""),
        failure("r9", "TC-9", "skipped", "", ""),
    ]
    for item in items:
        repo.add_result(item)
    return FailureAnalyzer(None, repo).analyze("run-1"), items


def three_runs() -> InMemoryRepository:
    repo = seeded_repo()
    for index, statuses in enumerate((("passed", "passed"), ("passed", "failed")), start=1):
        run_id = f"run-extra-{index}"
        repo.create_run(stored_run(run_id))
        for tc_id, status in zip(("TC-1", "TC-2"), statuses, strict=True):
            repo.add_result(stored_result(tc_id, status, run_id, result_id=f"{run_id}-{tc_id}"))
    return repo


def evidence_for(report_data: Any, folder: Path) -> Path:
    """Create the screenshot and snapshot files the report refers to."""
    folder.mkdir(parents=True, exist_ok=True)
    for test in report_data.tests:
        for name in (test.screenshot, test.dom_snapshot):
            if name:
                (folder / name).write_bytes(b"evidence")
    return folder


# ---------------------------------------------------------------------------- FR-20, FR-21


def test_at_fr20_settings_are_honoured_and_retries_are_recorded(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    """AT-FR-20: headless, timeouts, retries and workers are honoured; retries are recorded.

    Real PyTest subprocesses with a fake browser fixture (no Chromium needed).
    """
    marker = tmp_path / "seen-once"
    flaky = (
        "import os\n\ndef test_flaky(page):\n"
        f"    marker = {str(marker)!r}\n"
        "    if not os.path.exists(marker):\n"
        "        open(marker, 'w').close()\n"
        "        assert False, 'first attempt fails'\n"
    )
    probe = (
        "def test_probe(request):\n"
        "    assert request.config.getoption('aitaf_timeout_ms') == 1234\n"
        "    assert request.config.getoption('aitaf_headed') is True\n"
    )
    cases = {f"test_case_{i}": f"def test_case_{i}(page):\n    assert True\n" for i in range(4)}
    root = project(tmp_path, {"test_flaky": flaky, "test_probe": probe, **cases}, "<html></html>")
    base: dict[str, Any] = {
        "base_url": "http://127.0.0.1:8765",
        "allowed_hosts": ["127.0.0.1"],
        "run_timeout_s": 120,
    }
    config = RunConfig(
        scripts_dir=root,
        evidence_dir=tmp_path / "evidence",
        timeout_ms=1234,
        retries=2,
        workers=2,
        headless=False,
        **base,
    )
    summary = ExecutionEngine(repo).execute(config)
    stored = {r.tc_id: r for r in repo.list_results("run-1")}
    assert len(stored) == 6 and all(r.status == "passed" for r in stored.values())
    assert stored["TEST-FLAKY"].attempts == 2
    assert all(r.attempts == 1 for tc, r in stored.items() if tc != "TEST-FLAKY")
    for setting in ("headed", "workers 2", "timeout 1234 ms", "retries 2"):
        assert setting in summary.environment

    slow = project(
        tmp_path / "slow",
        {"test_slow": "import time\n\ndef test_slow(page):\n    time.sleep(30)\n"},
        "x",
    )
    with pytest.raises(ExecutionError, match="time limit"):
        ExecutionEngine(repo).execute(
            RunConfig(
                scripts_dir=slow, evidence_dir=tmp_path / "ev2", **{**base, "run_timeout_s": 3}
            )
        )


def test_at_fr21_a_non_listed_host_aborts_before_any_browser_action(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AT-FR-21: a non-listed URL aborts the run before any browser action, with the reason."""
    db = tmp_path / "blocked.db"
    code = main(
        [
            "execute",
            "--scripts",
            str(tmp_path),
            "--base-url",
            "http://203.0.113.9",
            "--db",
            str(db),
            "--evidence",
            str(tmp_path / "ev"),
        ]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "not on the allow-list" in err and "the run was not started" in err
    assert not (tmp_path / "ev").exists()
    stored = SqliteRepository(db)
    try:
        assert stored.list_runs_with_results() == []
    finally:
        stored.close()


# ---------------------------------------------------------------------------- FR-22 to FR-26


def test_at_fr22_a_locator_change_is_a_locator_failure_and_an_assertion_failure_is_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AT-FR-22: a locator change is a locator failure; an assertion failure is not."""
    assert main(heal_args("login_id_changed.html", db=tmp_path / "a.db")) == 0
    locator_out = capsys.readouterr().out
    assert "locator failure" in locator_out and "HEALED" in locator_out
    code = main(
        heal_args(
            "login_id_changed.html",
            "--error",
            "AssertionError",
            "--message",
            "assert 1 == 2",
            db=tmp_path / "b.db",
        )
    )
    defect_out = capsys.readouterr().out
    assert code == 1
    assert "application defect" in defect_out and "not healable" in defect_out.lower()
    assert "HEALED" not in defect_out.replace("NOT HEALED", "")


def test_at_fr23_repair_goes_in_cost_order_and_the_model_comes_last(
    repo: InMemoryRepository,
) -> None:
    """AT-FR-23: repair path recorded; the model step comes only after the first two fail."""
    provider = CountingProvider()
    engine = SelfHealingEngine(
        repo, HealingConfig(llm_enabled=True), LlmGateway(provider, repo, call_cap=20)
    )
    first = engine.heal(make_context("login_id_changed.html"))
    assert first.status is HealStatus.HEALED
    assert [(e.strategy_used, e.outcome) for e in first.events] == [("fallback", "proposed")]
    assert provider.calls == 0

    second = engine.heal(
        make_context("login_renamed.html", make_locator(CSS_ONLY), step="TC-1:step4")
    )
    assert second.status is HealStatus.HEALED
    assert [(e.strategy_used, e.outcome) for e in second.events] == [
        ("fallback", "no_candidate"),
        ("similarity", "no_candidate"),
        ("llm", "proposed"),
    ]
    assert provider.calls == 1
    assert second.events[-1].model and second.events[-1].prompt_version
    assert len(repo.list_healing_events("run-1")) == 4


def test_at_fr24_a_present_but_wrong_element_is_rejected_and_the_step_still_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AT-FR-24: a present but wrong element is rejected and the step still fails."""
    code = main(heal_args("login_wrong_element.html", db=tmp_path / "w.db"))
    out = capsys.readouterr().out
    assert code == 1
    assert "rejected" in out and "NOT HEALED" in out and "step still fails" in out


def test_at_fr25_healing_history_is_stored_and_a_permanent_update_needs_approval(
    repo: InMemoryRepository,
) -> None:
    """AT-FR-25: the healing history is populated; a permanent update without approval fails."""
    repo.add_locator("run-1", make_locator())
    engine = SelfHealingEngine(repo, HealingConfig())
    result = engine.heal(make_context("login_id_changed.html"))
    history = repo.list_healing_events("run-1")
    assert history == result.events and history
    event = history[0]
    assert event.outcome == "proposed" and not event.approved
    with pytest.raises(PolicyError, match="approval"):
        update_locator_from_event(repo, "run-1", event.event_id)
    assert repo.list_locators("run-1")[0].version == 1
    updated = approve_healing_event(repo, "run-1", event.event_id)
    assert updated.version == 2 and updated.primary == event.new_strategy


def test_at_fr26_attempt_limits_are_enforced_and_the_rate_is_in_the_report(
    repo: InMemoryRepository,
) -> None:
    """AT-FR-26: limits are configurable and enforced; the healing rate is in the report."""
    step_limited = SelfHealingEngine(repo, HealingConfig(max_attempts_per_step=1))
    assert step_limited.heal(make_context("login_id_changed.html")).status is HealStatus.HEALED
    assert step_limited.heal(make_context("login_id_changed.html")).status is (
        HealStatus.LIMIT_REACHED
    )
    run_limited = SelfHealingEngine(repo, HealingConfig(max_attempts_per_run=1))
    run_limited.heal(make_context("login_id_changed.html", step="a"))
    assert run_limited.heal(make_context("login_id_changed.html", step="b")).status is (
        HealStatus.LIMIT_REACHED
    )

    report = build_report(seeded_repo(), EXEC, SOURCE)
    metric = {m.key: m for m in report.metrics}["healing_success_rate"]
    assert metric.value == 0.5
    assert format_value(metric) in render_html(report) and metric.label in render_html(report)


# ---------------------------------------------------------------------------- FR-27 to FR-30


def test_at_fr27_every_failure_receives_a_category_and_accuracy_can_be_computed(
    repo: InMemoryRepository,
) -> None:
    """AT-FR-27: every failure on a labelled fixture set gets a category; accuracy is computed."""
    outcome, items = analysed(repo)
    failed = {r.tc_id for r in items if r.status in ("failed", "error")}
    assert {a.tc_id for a in outcome.analyses} == failed
    assert all(a.category in CATEGORIES for a in outcome.analyses)
    labels = {
        "TC-1": "locator",
        "TC-2": "locator",
        "TC-3": "assertion_defect",
        "TC-4": "environment",
        "TC-5": "timing_flaky",
        "TC-6": "timing_flaky",
        "TC-7": "unknown",
    }
    accuracy = {m.key: m for m in compute_metrics(repo, "run-1", None, labels)}[
        "classification_accuracy"
    ]
    assert accuracy.value is not None and 0.0 <= accuracy.value <= 1.0


def test_at_fr28_each_failure_has_a_cause_evidence_and_a_next_step(
    repo: InMemoryRepository,
) -> None:
    """AT-FR-28: each output contains a cause, references to the evidence used, and a next step."""
    outcome, _ = analysed(repo)
    assert outcome.analyses
    for analysis in outcome.analyses:
        assert analysis.root_cause.strip() and analysis.remediation.strip()
        assert any(ref.startswith("log:") for ref in analysis.evidence_refs)


def test_at_fr29_similar_failures_share_a_cluster_and_confidence_is_between_0_and_1(
    repo: InMemoryRepository,
) -> None:
    """AT-FR-29: same signature gives the same cluster ID; every confidence is from 0 to 1."""
    outcome, _ = analysed(repo)
    cluster = {a.tc_id: a.cluster_id for a in outcome.analyses}
    assert cluster["TC-5"] == cluster["TC-6"] != cluster["TC-3"]
    assert all(c.startswith("CL-") for c in cluster.values())
    assert all(0.0 <= a.confidence <= 1.0 for a in outcome.analyses)


def test_at_fr30_secrets_and_personal_data_do_not_reach_the_provider(
    repo: InMemoryRepository,
) -> None:
    """AT-FR-30: seeded secrets and personal data never reach the provider."""
    prompts: list[str] = []
    inner = MockProvider(responders={ANALYZER_COMPONENT: mock_extraction_responder})

    class Recorder:
        name = "mock"

        def complete(self, req: LlmRequest) -> LlmResponse:
            prompts.append(req.prompt)
            return inner.complete(req)

    text = "The system shall let admin@example.com sign in with password=Hunter2Hunter2 only."
    RequirementAnalyzer(LlmGateway(Recorder(), repo, call_cap=10), repo).analyze(
        [RawRequirement(source_ref="t.md#1", text=text)]
    )
    assert prompts
    joined = "\n".join(prompts)
    assert "admin@example.com" not in joined and "Hunter2Hunter2" not in joined
    audits = repo.list_audits("run-1")
    assert [a.input_hash for a in audits] == [input_hash(p) for p in prompts]
    key = "sk-live-ABCDEF1234567890ABCDEF12"
    assert key not in mask(f"the token {key} was rejected").text


# ---------------------------------------------------------------------------- FR-31 to FR-34


def test_at_fr31_the_html_report_opens_offline_and_links_every_screenshot_and_log(
    tmp_path: Path,
) -> None:
    """AT-FR-31: the report opens offline and links every screenshot and log it refers to."""
    data = build_report(seeded_repo(), EXEC, SOURCE)
    files = write_report(data, tmp_path / "out", evidence_for(data, tmp_path / "evidence"))
    page = files.html.read_text(encoding="utf-8")
    assert "<script" not in page and "http://" not in page and "https://" not in page
    links = {a or b for a, b in re.findall(r'(?:src|href)="([^"]+)"|\]\(([^)\s]+)\)', page)}
    assert links and all((files.html.parent / link).exists() for link in links)
    failed = [t for t in data.tests if t.status in ("failed", "error")]
    assert failed
    for test in failed:
        assert f"logs/{test.result_id}.txt" in page
        if test.screenshot:
            assert f"evidence/{test.screenshot}" in page


def test_at_fr32_markdown_and_pdf_come_from_one_data_model_with_identical_figures(
    tmp_path: Path,
) -> None:
    """AT-FR-32: Markdown and PDF are produced from one data model and show identical figures.

    PARTLY: the PDF is made here by an injected stub renderer from the same HTML file; the real
    Chromium PDF is exercised only in tests/integration/test_report_pdf.py.
    """
    data = build_report(seeded_repo(), EXEC, SOURCE)
    rendered: list[Path] = []

    def stub(html_path: Path, pdf_path: Path) -> None:
        rendered.append(html_path)
        pdf_path.write_bytes(b"%PDF-1.4 stub")

    files = write_report(data, tmp_path / "out", None, pdf_renderer=stub)
    html_text, md_text = render_html(data), render_markdown(data)
    for metric in data.metrics:
        assert format_value(metric) in html_text and format_value(metric) in md_text
    assert data.summary_line in html_text and data.summary_line in md_text
    assert files.pdf is not None and files.pdf.exists() and rendered == [files.html]


def test_at_fr33_a_trend_over_three_stored_runs_is_shown_and_traces_to_stored_data() -> None:
    """AT-FR-33: a trend over three or more stored runs is shown; metrics trace to stored data.

    PARTLY: the Dashboard shows pass rate, healing, accuracy, coverage, executability, latency and
    cost, but not code coverage (limitation L-002 in the defect log).
    """
    repo = three_runs()
    data = collect(repo)
    assert data.run_count == 3 and data.has_trend
    page = render_dashboard(data)
    assert "Trend over runs" in page and "Run table" in page and "needs at least" not in page
    for _, row in data.frame.iterrows():
        report = build_report(repo, row["run_id"])
        stored = {m.key: m.value for m in report.metrics}
        assert row["pass_rate"] == pytest.approx(stored["pass_rate"])
        assert row["requirement_coverage_ratio"] == stored["requirement_coverage_ratio"]


def test_at_fr34_one_query_returns_the_full_chain_for_a_result_and_the_reverse() -> None:
    """AT-FR-34: a single query returns the full chain for any test result, and the reverse."""
    data = build_report(seeded_repo(), EXEC, SOURCE)
    row = trace_for_result(data, "res-TC-2")
    assert row is not None
    assert (row.requirement_id, row.tc_id, row.script_path, row.status) == (
        "R1",
        "TC-2",
        "tests/test_tc-2.py",
        "failed",
    )
    assert row.analysis_category == "locator" and row.cluster_id
    for entry in data.trace:
        if entry.script_path:
            assert entry.requirement_id and entry.requirement_ref
    assert [r.tc_id for r in trace_for_requirement(data, "R1")] == ["TC-1", "TC-2"]


# ---------------------------------------------------------------------------- FR-35 to FR-39


COMMANDS = (
    "run",
    "analyze",
    "generate",
    "script",
    "execute",
    "diagnose",
    "report",
    "dashboard",
    "approve-heal",
    "evaluate",
    "review",
    "heal",
    "metrics",
)


def test_at_fr35_run_and_every_stage_command_exist_and_bad_configuration_is_rejected(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AT-FR-35: run, stage commands and --help exist; invalid configuration is rejected."""
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    overview = capsys.readouterr().out
    for command in COMMANDS:
        assert command in overview
        with pytest.raises(SystemExit) as sub:
            main([command, "--help"])
        assert sub.value.code == 0 and capsys.readouterr().out.strip()
    monkeypatch.setenv("LLM_PROVIDER", "banana")
    code = main(["analyze", "--input", str(SAMPLE_PLAIN), "--db", str(tmp_path / "x.db")])
    assert code == 2 and "LLM_PROVIDER" in capsys.readouterr().err


def test_at_fr36_with_the_api_unreachable_the_pipeline_completes_and_says_mock(
    tmp_path: Path,
) -> None:
    """AT-FR-36: with the API down the pipeline completes and marks output mock-generated."""
    db = tmp_path / "down.db"
    process = cli(
        "analyze",
        "--input",
        str(SAMPLE_PLAIN),
        "--db",
        str(db),
        extra_env={
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-not-a-real-key-for-tests",
            "OPENAI_BASE_URL": "http://127.0.0.1:9",
            "LLM_MAX_RETRIES": "0",
            "LLM_TIMEOUT_S": "2",
        },
    )
    assert process.returncode == 0, process.stderr[-500:]
    assert "mock-generated" in process.stdout and "AI-generated output from" not in process.stdout
    stored = SqliteRepository(db)
    try:
        run_id = stored.latest_run_with_requirements()
        assert run_id is not None and stored.list_requirements(run_id)
        assert {a.status for a in stored.list_audits(run_id)} == {"fallback"}
    finally:
        stored.close()


def test_at_fr37_exactly_one_audit_record_per_call_and_no_secret_or_prompt_in_the_table(
    tmp_path: Path,
) -> None:
    """AT-FR-37: one audit record per LLM call; no secret or raw prompt in the audit table."""
    db = tmp_path / "audit.db"
    stored = SqliteRepository(db)
    stored.create_run(stored_run("run-1"))
    set_run_id("run-1")
    seen: list[str] = []

    class FailsOnThird:
        name = "openai"

        def complete(self, req: LlmRequest) -> LlmResponse:
            seen.append(req.prompt)
            if len(seen) == 3:
                raise LlmTransientError("simulated outage")
            return LlmResponse(text="{}", model="gpt-test", tokens_in=2, tokens_out=1, mock=False)

    secret, marker = "sk-live-ABCDEF1234567890ABCDEF12", "RAW-PROMPT-MARKER-4711"
    gateway = LlmGateway(FailsOnThird(), stored, call_cap=10, fallback=MockProvider())
    try:
        for index in range(3):
            gateway.complete(
                LlmRequest(
                    component="demo", prompt_version="d-1", prompt=f"{marker} {secret} call {index}"
                )
            )
        audits = stored.list_audits("run-1")
        assert len(audits) == 3 and len({a.call_id for a in audits}) == 3
        assert [a.status for a in audits] == ["ok", "ok", "fallback"]
    finally:
        set_run_id("")
        stored.close()
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT * FROM llm_audit").fetchall()
    dump = " ".join(str(value) for row in rows for value in row)
    assert len(rows) == 3 and marker not in dump and secret not in dump


def test_at_fr38_the_same_seed_gives_the_same_mutations_and_healing_is_reported_per_kind() -> None:
    """AT-FR-38: the same seed gives the same mutations; healing is reported per mutation type."""
    assert select_mutations(7, 12) == select_mutations(7, 12)
    assert select_mutations(7, 12) != select_mutations(8, 12)
    first = run_healing_evaluation(seed=7, count=12, controls=False)
    second = run_healing_evaluation(seed=7, count=12, controls=False)
    assert [(t.trial_id, t.mutation_id, t.healed, t.correct) for t in first] == [
        (t.trial_id, t.mutation_id, t.healed, t.correct) for t in second
    ]
    per_kind = healing_by_kind(first)
    assert per_kind and sum(trials for _, trials, _, _ in per_kind) == 12
    assert all(0 <= correct <= repaired <= trials for _, trials, repaired, correct in per_kind)


def test_at_fr39_metrics_are_exported_as_csv_with_at_least_two_quantitative_values(
    tmp_path: Path,
) -> None:
    """AT-FR-39: metrics are exported as CSV; at least two quantitative metrics exist."""
    data = build_report(seeded_repo(), EXEC, SOURCE)
    files = write_report(data, tmp_path / "out", None)
    with files.metrics_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert set(rows[0]) == {"key", "label", "value", "unit", "basis", "provider"}
    numeric = [r for r in rows if r["value"] != ""]
    assert len(numeric) >= 2
    assert {"pass_rate", "requirement_coverage_ratio"} <= {r["key"] for r in numeric}
