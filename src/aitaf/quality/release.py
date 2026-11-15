"""Release helpers used by the release workflow.

``notes`` prints the changelog section of a version (the GitHub Release body);
``check`` refuses a tag that does not match the package version, so a tag can never
publish a release under the wrong number.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import aitaf
from aitaf.core.errors import AitafError, ConfigError


def changelog_section(text: str, version: str) -> str:
    """Body of the ``## [version]`` section of a Keep a Changelog file."""
    bare = version.removeprefix("v")
    heading = re.search(rf"^## \[{re.escape(bare)}\][^\n]*\n", text, re.MULTILINE)
    if heading is None:
        raise ConfigError(f"no changelog section for version {bare}")
    rest = text[heading.end() :]
    following = re.search(r"^## \[", rest, re.MULTILINE)
    body = (rest[: following.start()] if following else rest).strip()
    if not body:
        raise ConfigError(f"the changelog section for version {bare} is empty")
    return body


def check_version(tag: str, package_version: str) -> None:
    if tag.removeprefix("v") != package_version:
        raise ConfigError(f"tag {tag} does not match package version {package_version}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aitaf.quality.release", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    notes = commands.add_parser("notes", help="print the changelog section of a version")
    notes.add_argument("changelog")
    notes.add_argument("version")
    check = commands.add_parser("check", help="check a tag against the package version")
    check.add_argument("tag")
    args = parser.parse_args(argv)
    try:
        if args.command == "notes":
            try:
                text = Path(args.changelog).read_text(encoding="utf-8")
            except OSError as exc:
                raise ConfigError(f"cannot read {args.changelog}: {exc.strerror}") from exc
            print(changelog_section(text, args.version))
        else:
            check_version(args.tag, aitaf.__version__)
            print(f"tag {args.tag} matches package version {aitaf.__version__}")
    except AitafError as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
