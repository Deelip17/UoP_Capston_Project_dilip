"""Command-line interface (FR-35).

``aitaf run`` runs the whole pipeline and one command exists per stage. Every
command validates the configuration file first and rejects invalid settings with
a clear message (exit code 2). ``analyze``, ``generate``, ``review``, ``script``,
``metrics`` and ``heal`` (a stand-alone demonstration of the Self-Healing Engine on
DOM snapshots) are implemented; the other stages report that they are not implemented
yet (exit code 3) until their slices land.
"""

from __future__ import annotations

import argparse
import platform
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from aitaf.analyzer import COMPONENT as ANALYZER_COMPONENT
from aitaf.analyzer import RequirementAnalyzer, load_requirements, mock_extraction_responder
from aitaf.core.config import Settings
from aitaf.core.errors import AitafError, ConfigError, PersistenceError, ValidationError
from aitaf.core.healing import FailureContext, FailureKind, HealStatus
from aitaf.core.llm import LlmGateway, build_providers
from aitaf.core.logging import configure_root, new_run_id, set_run_id
from aitaf.core.metrics import Metrics, run_cost, summarise
from aitaf.core.models import Locator, LocatorStrategy, ReviewStatus, Run, RunStatus
from aitaf.core.storage import Repository, SqliteRepository
from aitaf.execution import ExecutionEngine, RunConfig
from aitaf.execution.runner import describe_environment
from aitaf.generator import COMPONENT as GENERATOR_COMPONENT
from aitaf.generator import (
    TestCaseGenerator,
    cases_for_scripting,
    export_cases,
    mock_generation_responder,
    set_review_status,
)
from aitaf.healing import COMPONENT as HEALING_COMPONENT
from aitaf.healing import (
    HealingConfig,
    SelfHealingEngine,
    find_elements,
    mock_healing_responder,
    parse_dom,
    signature_of,
)
from aitaf.scriptgen import COMPONENT as SCRIPT_COMPONENT
from aitaf.scriptgen import ScriptGenerator, mock_script_responder

STAGES: dict[str, str] = {
    "analyze": "Requirement Analyzer: turn requirements into structured records",
    "generate": "Test Case Generator: create test cases from analysed requirements",
    "script": "Script Generator: create executable test scripts",
    "execute": "Execution Engine: run the scripts (with Self-Healing Engine)",
    "diagnose": "Failure Analyzer: classify failures",
    "report": "Reporting Engine: produce the run report",
}

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_NOT_IMPLEMENTED = 3

_MOCK_NOTE = "mock-generated output, review before use"


def _output_note(settings: Settings) -> str:
    """Label the output by provider so live text is never shown as mock (NFR-30)."""
    if settings.llm_provider == "mock":
        return _MOCK_NOTE
    return (
        f"AI-generated output from {settings.llm_model} via OpenAI "
        "(a failed call falls back to mock, see the audit), review before use"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aitaf", description="AI-powered test automation framework (capstone prototype)"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")
    commands.add_parser("run", help="run the whole pipeline").add_argument(
        "--config", help="path to the JSON configuration file"
    )
    for name, description in STAGES.items():
        stage = commands.add_parser(name, help=description)
        stage.add_argument("--config", help="path to the JSON configuration file")
        if name in ("analyze", "generate", "script", "execute"):
            stage.add_argument("--db", default="aitaf.db", help="SQLite database path")
        if name == "analyze":
            stage.add_argument("--input", required=True, help="requirements file (.txt, .md)")
        if name == "generate":
            stage.add_argument("--export-dir", help="also export cases as JSON, CSV and Markdown")
        if name == "script":
            stage.add_argument("--out-dir", default="generated_tests", help="output directory")
            stage.add_argument(
                "--framework", choices=["playwright", "selenium"], default="playwright"
            )
            stage.add_argument("--base-url", default="http://localhost:8000")
            stage.add_argument(
                "--allow-host",
                action="append",
                default=[],
                help="host the scripts may target (repeatable); localhost is always allowed",
            )
            stage.add_argument(
                "--no-review",
                action="store_true",
                help="also script Pending cases (Rejected cases are never scripted)",
            )
    _add_execute_options(commands.choices["execute"])
    heal = commands.add_parser("heal", help="demonstrate locator healing on two DOM snapshots")
    heal.add_argument("--config", help="path to the JSON configuration file")
    heal.add_argument("--db", default="aitaf.db", help="SQLite database path")
    heal.add_argument("--before", required=True, help="HTML snapshot where the locator worked")
    heal.add_argument("--after", required=True, help="HTML snapshot where the step failed")
    heal.add_argument(
        "--primary", required=True, metavar="KIND=VALUE", help="stored primary locator"
    )
    heal.add_argument(
        "--fallback", action="append", default=[], metavar="KIND=VALUE", help="stored fallback"
    )
    heal.add_argument("--name", default="target", help="locator name")
    heal.add_argument(
        "--action",
        default="click",
        choices=["click", "type", "select", "assert_text", "assert_visible"],
    )
    heal.add_argument("--error", default="NoSuchElementException", help="exception type")
    heal.add_argument("--message", default="", help="exception message")
    heal.add_argument(
        "--llm",
        action="store_true",
        help="enable the LLM rung (provider from LLM_PROVIDER; mock by default)",
    )
    report = commands.add_parser("metrics", help="show latency, token and cost metrics of a run")
    report.add_argument("--config", help="path to the JSON configuration file")
    report.add_argument("--db", default="aitaf.db", help="SQLite database path")
    report.add_argument("--run", help="run ID (default: the latest run with metrics)")
    review = commands.add_parser("review", help="review generated test cases (human gate)")
    review.add_argument("--config", help="path to the JSON configuration file")
    review.add_argument("--db", default="aitaf.db", help="SQLite database path")
    review.add_argument("--list", action="store_true", help="list test cases (default action)")
    review.add_argument("--status", choices=[s.value for s in ReviewStatus], help="filter --list")
    review.add_argument("--approve", metavar="TC_ID", help="approve a test case")
    review.add_argument("--reject", metavar="TC_ID", help="reject a test case")
    return parser


def _add_execute_options(stage: argparse.ArgumentParser) -> None:
    stage.add_argument("--scripts", required=True, help="directory written by 'aitaf script'")
    stage.add_argument("--base-url", required=True, help="system under test (must be allow-listed)")
    stage.add_argument(
        "--allow-host",
        action="append",
        default=[],
        help="host the run may target (repeatable); localhost and 127.0.0.1 are always allowed",
    )
    stage.add_argument("--evidence", default="reports/runs", help="screenshots, DOM, JUnit output")
    stage.add_argument("--driver", choices=["playwright", "selenium"], default="playwright")
    stage.add_argument("--headed", action="store_true", help="show the browser (default headless)")
    stage.add_argument("--timeout-ms", type=int, default=10_000, help="default action timeout")
    stage.add_argument("--retries", type=int, default=0, help="reruns of a failing test (0 to 5)")
    stage.add_argument("--workers", type=int, default=1, help="parallel workers (1 to 8)")
    stage.add_argument("--checkpoints", action="store_true", help="also screenshot passing tests")
    stage.add_argument("--run-timeout-s", type=int, default=600, help="time limit for the run")


def _gateway(settings: Settings, repo: Repository, metrics: Metrics | None = None) -> LlmGateway:
    provider, fallback = build_providers(
        settings,
        responders={
            ANALYZER_COMPONENT: mock_extraction_responder,
            GENERATOR_COMPONENT: mock_generation_responder,
            SCRIPT_COMPONENT: mock_script_responder,
            HEALING_COMPONENT: mock_healing_responder,
        },
    )
    return LlmGateway(
        provider,
        repo,
        call_cap=settings.llm_call_cap,
        fallback=fallback,
        metrics=metrics,
        price_in_per_1k=settings.llm_price_in_per_1k,
        price_out_per_1k=settings.llm_price_out_per_1k,
    )


def _analyze(settings: Settings, args: argparse.Namespace) -> int:
    repo = SqliteRepository(args.db)
    try:
        repo.recover_interrupted_runs()
        run_id = new_run_id()
        set_run_id(run_id)
        repo.create_run(
            Run(
                run_id=run_id,
                started_at=datetime.now(UTC),
                status=RunStatus.RUNNING,
                provider=settings.llm_provider,
                environment=f"python{platform.python_version()}-{platform.system()}",
            )
        )
        try:
            metrics = Metrics(repo)
            result = RequirementAnalyzer(
                _gateway(settings, repo, metrics), repo, metrics=metrics
            ).analyze(load_requirements(args.input))
        except AitafError:
            repo.finish_run(run_id, RunStatus.FAILED, datetime.now(UTC))
            raise
        repo.finish_run(run_id, RunStatus.COMPLETED, datetime.now(UTC))
    finally:
        repo.close()

    print(f"run {run_id} ({_output_note(settings)})")
    for record in result.ready:
        print(f"READY    {record.req_id}  {record.risk.value:<6}  {record.source_ref}")
    for record in result.flagged:
        print(f"FLAGGED  {record.req_id}  {record.risk.value:<6}  {record.source_ref}")
        for flag in record.ambiguity_flags:
            print(f"           - {flag}")
    for _source_ref, reason in result.rejected:
        print(f"REJECTED {reason}")
    print(
        f"summary: {len(result.ready)} ready, {len(result.flagged)} flagged, "
        f"{len(result.rejected)} rejected"
    )
    return EXIT_OK


def _latest_run(repo: Repository) -> str:
    run_id = repo.latest_run_with_requirements()
    if run_id is None:
        raise PersistenceError("no analysed requirements found; run 'aitaf analyze' first")
    return run_id


def _generate(settings: Settings, args: argparse.Namespace) -> int:
    repo = SqliteRepository(args.db)
    try:
        run_id = _latest_run(repo)
        set_run_id(run_id)
        requirements = repo.list_requirements(run_id)
        metrics = Metrics(repo)
        result = TestCaseGenerator(
            _gateway(settings, repo, metrics), repo, metrics=metrics
        ).generate(requirements)
        if args.export_dir:
            export_cases(result.cases, Path(args.export_dir))
    finally:
        repo.close()

    print(f"run {run_id} ({_output_note(settings)})")
    for case in result.cases:
        print(f"{case.tc_id}  {case.priority}  {case.review_status.value:<8}  {case.title}")
    for req_id, reason in result.skipped:
        print(f"SKIPPED  {req_id}: {reason}")
    for gap in result.coverage_gaps:
        print(f"GAP      {gap}")
    print(
        f"summary: {len(result.cases)} test cases, {len(result.scenarios)} scenarios, "
        f"{len(result.skipped)} skipped, {result.duplicates_removed} duplicates removed, "
        f"{result.data_replaced} data values replaced, {len(result.coverage_gaps)} coverage gaps"
    )
    print("all new cases are Pending; approve with: aitaf review --approve TC_ID")
    return EXIT_OK


def _script(settings: Settings, args: argparse.Namespace) -> int:
    repo = SqliteRepository(args.db)
    try:
        run_id = _latest_run(repo)
        set_run_id(run_id)
        cases = cases_for_scripting(repo, run_id, review_mode=not args.no_review)
        hosts = frozenset({"localhost", "127.0.0.1", *args.allow_host})
        metrics = Metrics(repo)
        generator = ScriptGenerator(
            _gateway(settings, repo, metrics),
            repo,
            framework=args.framework,
            base_url=args.base_url,
            allowed_hosts=hosts,
            output_dir=Path(args.out_dir),
            metrics=metrics,
        )
        result = generator.generate(cases, repo.list_test_data(run_id))
    finally:
        repo.close()

    print(f"run {run_id} ({_output_note(settings)})")
    for script in result.scripts:
        print(f"{script.script_id}  {script.path}")
    for tc_id, reasons in result.rejected:
        print(f"REJECTED {tc_id}:")
        for reason in reasons:
            print(f"           - {reason}")
    print(
        f"summary: {len(result.scripts)} scripts written ({args.framework}), "
        f"{len(result.rejected)} rejected, {len(result.locators)} locators, "
        f"static validation passed for every saved file"
    )
    if not cases:
        print("no test cases are approved yet; approve with: aitaf review --approve TC_ID")
    else:
        print(f"run them with: pytest {args.out_dir} --base-url {args.base_url}")
    return EXIT_OK


_STATUS_LABEL = {"passed": "PASSED ", "failed": "FAILED ", "error": "ERROR  ", "skipped": "SKIPPED"}


def _execute(settings: Settings, args: argparse.Namespace) -> int:
    run_id = new_run_id()
    try:
        config = RunConfig(
            scripts_dir=Path(args.scripts),
            base_url=args.base_url,
            allowed_hosts=tuple({"localhost", "127.0.0.1", *args.allow_host}),
            evidence_dir=Path(args.evidence) / run_id,
            driver=args.driver,
            headless=not args.headed,
            timeout_ms=args.timeout_ms,
            retries=args.retries,
            workers=args.workers,
            checkpoints=args.checkpoints,
            run_timeout_s=args.run_timeout_s,
        )
    except ValueError as exc:
        raise ConfigError(str(exc).splitlines()[0]) from exc
    repo = SqliteRepository(args.db)
    try:
        repo.recover_interrupted_runs()
        set_run_id(run_id)
        repo.create_run(
            Run(
                run_id=run_id,
                started_at=datetime.now(UTC),
                status=RunStatus.RUNNING,
                provider=settings.llm_provider,
                environment=describe_environment(config),
            )
        )
        try:
            summary = ExecutionEngine(repo, Metrics(repo)).execute(config)
        except AitafError:
            repo.finish_run(run_id, RunStatus.FAILED, datetime.now(UTC))
            raise
        repo.finish_run(run_id, RunStatus.COMPLETED, datetime.now(UTC))
    finally:
        repo.close()

    print(f"run {run_id} ({summary.environment})")
    for test in summary.executed:
        extra = f"  screenshot={test.screenshot}" if test.screenshot else ""
        print(
            f"{_STATUS_LABEL.get(test.status, test.status)}  {test.tc_id}  {test.duration_ms} ms  "
            f"attempts={test.attempts}{extra}"
        )
    print(
        f"summary: {summary.passed} passed, {summary.failed} failed, {summary.errors} errors, "
        f"{summary.skipped} skipped; evidence in {config.evidence_dir}"
    )
    return EXIT_OK if summary.all_passed else EXIT_FAILURE


_STRATEGY_KINDS = ("id", "css", "xpath", "text", "role", "attr")
_KIND_LABELS = {
    FailureKind.LOCATOR: "locator failure",
    FailureKind.APPLICATION_DEFECT: "application defect",
    FailureKind.UNKNOWN: "unknown failure",
}


def _strategy_arg(text: str) -> LocatorStrategy:
    kind, sep, value = text.partition("=")
    if not sep or kind not in _STRATEGY_KINDS or not value:
        raise ConfigError(
            f"locator must look like kind=value with kind one of {', '.join(_STRATEGY_KINDS)}; "
            f"got {text!r}"
        )
    return LocatorStrategy(kind=kind, value=value)  # type: ignore[arg-type]


def _read_snapshot(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc


def _show(strategy: LocatorStrategy | None) -> str:
    return f"{strategy.kind}={strategy.value}" if strategy else "-"


def _heal(settings: Settings, args: argparse.Namespace) -> int:
    primary = _strategy_arg(args.primary)
    fallbacks = [_strategy_arg(item) for item in args.fallback]
    before = parse_dom(_read_snapshot(args.before))
    found = find_elements(before, primary)
    if not found:
        raise ValidationError("the primary locator does not resolve in the --before page")
    baseline = signature_of(before, found[0])
    locator = Locator(
        loc_id=f"cli.{args.name}",
        page="cli",
        name=args.name,
        primary=primary,
        fallbacks=fallbacks,
        model="cli-demo",
        prompt_version="n/a",
    )
    repo = SqliteRepository(args.db)
    try:
        run_id = new_run_id()
        set_run_id(run_id)
        repo.create_run(
            Run(
                run_id=run_id,
                started_at=datetime.now(UTC),
                status=RunStatus.RUNNING,
                provider=settings.llm_provider,
                environment=f"python{platform.python_version()}-{platform.system()}",
            )
        )
        metrics = Metrics(repo)
        engine = SelfHealingEngine(
            repo,
            HealingConfig(llm_enabled=args.llm),
            _gateway(settings, repo, metrics) if args.llm else None,
            metrics=metrics,
        )
        result = engine.heal(
            FailureContext(
                step_ref=f"cli:{args.name}",
                action=args.action,
                locator=locator,
                error_type=args.error,
                error_message=args.message,
                dom_html=_read_snapshot(args.after),
                baseline=baseline,
            )
        )
        repo.finish_run(run_id, RunStatus.COMPLETED, datetime.now(UTC))
    finally:
        repo.close()

    print(f"run {run_id} ({_output_note(settings)})")
    print(f"failure: {_KIND_LABELS[result.kind]} ({args.error})")
    shown = " ".join(f'{k}="{v}"' for k, v in baseline.attrs.items() if k in ("id", "type", "name"))
    print(f'baseline: {baseline.tag} {shown} text="{baseline.text}" (from --before)')
    for event in result.events:
        detail = f"confidence {event.confidence:.2f}" if event.outcome != "no_candidate" else ""
        extra = f"  [{event.reason}]" if event.reason else ""
        print(
            f"attempt  {event.strategy_used:<11} {_show(event.new_strategy):<28} "
            f"{event.outcome:<13} {detail}{extra}"
        )
    if result.status is HealStatus.HEALED:
        print(
            f"result: HEALED via {_show(result.strategy)} (confidence {result.confidence:.2f}); "
            "proposed, awaiting human approval"
        )
        return EXIT_OK
    if result.status is HealStatus.NOT_HEALABLE:
        print(f"result: not healable: {result.reason} (a real defect must stay visible)")
    else:
        print(f"result: NOT HEALED: {result.reason}")
    return EXIT_FAILURE


def _metrics(args: argparse.Namespace) -> int:
    repo = SqliteRepository(args.db)
    try:
        run_id = args.run or repo.latest_run_with_metrics()
        samples = repo.list_metrics(run_id) if run_id else []
    finally:
        repo.close()
    if not samples:
        suffix = f" for run {args.run}" if args.run else ""
        raise PersistenceError(f"no metrics recorded{suffix}")
    print(f"run {run_id}")
    print(
        f"{'component':<22}{'operation':<22}{'count':>6}{'errors':>7}"
        f"{'median_ms':>11}{'tokens_in':>10}{'tokens_out':>11}{'cost_usd':>10}"
    )
    for row in summarise(samples):
        print(
            f"{row.component:<22}{row.operation:<22}{row.count:>6}{row.errors:>7}"
            f"{row.median_ms:>11.2f}{row.tokens_in:>10}{row.tokens_out:>11}{row.cost_usd:>10.4f}"
        )
    print(f"total cost: ${run_cost(samples):.4f}")
    return EXIT_OK


def _review(args: argparse.Namespace) -> int:
    repo = SqliteRepository(args.db)
    try:
        run_id = _latest_run(repo)
        if args.approve:
            set_review_status(repo, run_id, args.approve, ReviewStatus.APPROVED)
            print(f"{args.approve} -> Approved")
        if args.reject:
            set_review_status(repo, run_id, args.reject, ReviewStatus.REJECTED)
            print(f"{args.reject} -> Rejected")
        if args.list or not (args.approve or args.reject):
            status = ReviewStatus(args.status) if args.status else None
            for case in repo.list_test_cases(run_id, status):
                print(f"{case.tc_id}  {case.review_status.value:<8}  {case.title}")
    finally:
        repo.close()
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.from_file(args.config) if args.config else Settings.from_env()
    except AitafError as exc:
        print(f"aitaf: invalid configuration: {exc}", file=sys.stderr)
        return EXIT_USAGE
    configure_root(settings.log_level)
    handlers = {
        "analyze": lambda: _analyze(settings, args),
        "generate": lambda: _generate(settings, args),
        "review": lambda: _review(args),
        "script": lambda: _script(settings, args),
        "execute": lambda: _execute(settings, args),
        "heal": lambda: _heal(settings, args),
        "metrics": lambda: _metrics(args),
    }
    handler = handlers.get(args.command)
    if handler is None:
        print(f"aitaf: command '{args.command}' is not implemented yet", file=sys.stderr)
        return EXIT_NOT_IMPLEMENTED
    try:
        return handler()
    except ConfigError as exc:
        print(f"aitaf: invalid configuration: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except AitafError as exc:
        print(f"aitaf: {args.command} failed: {exc}", file=sys.stderr)
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
