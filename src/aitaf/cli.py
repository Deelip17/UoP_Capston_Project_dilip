"""Command-line interface skeleton (FR-35).

``aitaf run`` runs the whole pipeline and one command exists per stage. Every
command validates the configuration file first and rejects invalid settings with
a clear message (exit code 2). The stage logic arrives in later slices; until
then a valid command reports that the stage is not implemented (exit code 3).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from aitaf.core.config import Settings
from aitaf.core.errors import AitafError
from aitaf.core.logging import configure_root

STAGES: dict[str, str] = {
    "analyze": "Requirement Analyzer: turn requirements into structured records",
    "generate": "Test Case Generator: create test cases from analysed requirements",
    "script": "Script Generator: create executable test scripts",
    "execute": "Execution Engine: run the scripts (with Self-Healing Engine)",
    "diagnose": "Failure Analyzer: classify failures",
    "report": "Reporting Engine: produce the run report",
}

EXIT_OK = 0
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
        commands.add_parser(name, help=description).add_argument(
            "--config", help="path to the JSON configuration file"
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.from_file(args.config) if args.config else Settings.from_env()
    except AitafError as exc:
        print(f"aitaf: invalid configuration: {exc}", file=sys.stderr)
        return EXIT_USAGE
    configure_root(settings.log_level)
    print(f"aitaf: command '{args.command}' is not implemented yet", file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":
    sys.exit(main())
