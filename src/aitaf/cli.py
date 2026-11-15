"""Command-line interface (FR-35).

``aitaf run`` runs the whole pipeline and one command exists per stage. Every
command validates the configuration file first and rejects invalid settings with
a clear message (exit code 2). ``analyze`` is implemented; the other stages
report that they are not implemented yet (exit code 3) until their slices land.
"""

from __future__ import annotations

import argparse
import platform
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from aitaf.analyzer import COMPONENT, RequirementAnalyzer, load_requirements
from aitaf.analyzer import mock_extraction_responder as _mock_extraction
from aitaf.core.config import Settings
from aitaf.core.errors import AitafError, ConfigError
from aitaf.core.llm import LlmGateway, MockProvider
from aitaf.core.logging import configure_root, new_run_id, set_run_id
from aitaf.core.models import Run, RunStatus
from aitaf.core.storage import SqliteRepository

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
        if name == "analyze":
            stage.add_argument("--input", required=True, help="requirements file (.txt, .md)")
            stage.add_argument("--db", default="aitaf.db", help="SQLite database path")
    return parser


def _analyze(settings: Settings, input_path: str, db_path: str) -> int:
    if settings.llm_provider != "mock":
        raise ConfigError("only the mock LLM provider is available in this build")
    repo = SqliteRepository(db_path)
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
        provider = MockProvider(responders={COMPONENT: _mock_extraction})
        gateway = LlmGateway(provider, repo, call_cap=settings.llm_call_cap)
        try:
            result = RequirementAnalyzer(gateway, repo).analyze(load_requirements(input_path))
        except AitafError:
            repo.finish_run(run_id, RunStatus.FAILED, datetime.now(UTC))
            raise
        repo.finish_run(run_id, RunStatus.COMPLETED, datetime.now(UTC))
    finally:
        repo.close()

    print(f"run {run_id} (mock-generated output, review before use)")
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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.from_file(args.config) if args.config else Settings.from_env()
    except AitafError as exc:
        print(f"aitaf: invalid configuration: {exc}", file=sys.stderr)
        return EXIT_USAGE
    configure_root(settings.log_level)
    if args.command == "analyze":
        try:
            return _analyze(settings, args.input, args.db)
        except ConfigError as exc:
            print(f"aitaf: invalid configuration: {exc}", file=sys.stderr)
            return EXIT_USAGE
        except AitafError as exc:
            print(f"aitaf: analyze failed: {exc}", file=sys.stderr)
            return EXIT_FAILURE
    print(f"aitaf: command '{args.command}' is not implemented yet", file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":
    sys.exit(main())
