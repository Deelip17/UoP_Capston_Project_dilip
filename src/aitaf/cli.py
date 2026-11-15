"""Command-line interface (FR-35).

``aitaf run`` runs the whole pipeline and one command exists per stage. Every
command validates the configuration file first and rejects invalid settings with
a clear message (exit code 2). ``analyze``, ``generate``, ``review`` and ``script``
are implemented; the other stages report that they are not implemented yet (exit
code 3) until their slices land.
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
from aitaf.core.errors import AitafError, ConfigError, PersistenceError
from aitaf.core.llm import LlmGateway, MockProvider
from aitaf.core.logging import configure_root, new_run_id, set_run_id
from aitaf.core.models import ReviewStatus, Run, RunStatus
from aitaf.core.storage import Repository, SqliteRepository
from aitaf.generator import COMPONENT as GENERATOR_COMPONENT
from aitaf.generator import (
    TestCaseGenerator,
    cases_for_scripting,
    export_cases,
    mock_generation_responder,
    set_review_status,
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
        if name in ("analyze", "generate", "script"):
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
    review = commands.add_parser("review", help="review generated test cases (human gate)")
    review.add_argument("--config", help="path to the JSON configuration file")
    review.add_argument("--db", default="aitaf.db", help="SQLite database path")
    review.add_argument("--list", action="store_true", help="list test cases (default action)")
    review.add_argument("--status", choices=[s.value for s in ReviewStatus], help="filter --list")
    review.add_argument("--approve", metavar="TC_ID", help="approve a test case")
    review.add_argument("--reject", metavar="TC_ID", help="reject a test case")
    return parser


def _require_mock(settings: Settings) -> None:
    if settings.llm_provider != "mock":
        raise ConfigError("only the mock LLM provider is available in this build")


def _gateway(settings: Settings, repo: Repository) -> LlmGateway:
    provider = MockProvider(
        responders={
            ANALYZER_COMPONENT: mock_extraction_responder,
            GENERATOR_COMPONENT: mock_generation_responder,
            SCRIPT_COMPONENT: mock_script_responder,
        }
    )
    return LlmGateway(provider, repo, call_cap=settings.llm_call_cap)


def _analyze(settings: Settings, args: argparse.Namespace) -> int:
    _require_mock(settings)
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
            result = RequirementAnalyzer(_gateway(settings, repo), repo).analyze(
                load_requirements(args.input)
            )
        except AitafError:
            repo.finish_run(run_id, RunStatus.FAILED, datetime.now(UTC))
            raise
        repo.finish_run(run_id, RunStatus.COMPLETED, datetime.now(UTC))
    finally:
        repo.close()

    print(f"run {run_id} ({_MOCK_NOTE})")
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
    _require_mock(settings)
    repo = SqliteRepository(args.db)
    try:
        run_id = _latest_run(repo)
        set_run_id(run_id)
        requirements = repo.list_requirements(run_id)
        result = TestCaseGenerator(_gateway(settings, repo), repo).generate(requirements)
        if args.export_dir:
            export_cases(result.cases, Path(args.export_dir))
    finally:
        repo.close()

    print(f"run {run_id} ({_MOCK_NOTE})")
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
    _require_mock(settings)
    repo = SqliteRepository(args.db)
    try:
        run_id = _latest_run(repo)
        set_run_id(run_id)
        cases = cases_for_scripting(repo, run_id, review_mode=not args.no_review)
        hosts = frozenset({"localhost", "127.0.0.1", *args.allow_host})
        generator = ScriptGenerator(
            _gateway(settings, repo),
            repo,
            framework=args.framework,
            base_url=args.base_url,
            allowed_hosts=hosts,
            output_dir=Path(args.out_dir),
        )
        result = generator.generate(cases, repo.list_test_data(run_id))
    finally:
        repo.close()

    print(f"run {run_id} ({_MOCK_NOTE})")
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
