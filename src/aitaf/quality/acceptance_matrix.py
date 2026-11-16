"""Acceptance matrix: requirement, criterion, test and result in one table (NFR-20, ADR-047).

A test belongs to a requirement when the first line of its docstring starts with ``AT-FR-nn``.
A line ``PARTLY: ...`` in the docstring says what the test does not demonstrate; a passing test
with such a line is reported as "Partly met", never as "Met". Results come from JUnit XML files
written by ``pytest --junitxml``; without a result the row says "No result", and a requirement
without a test says "No test", so a gap cannot hide.

Run: ``python -m aitaf.quality.acceptance_matrix --junit reports/a.xml --out matrix.md``.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

_TOKEN = re.compile(r"^AT-(FR-\d+)\b")
_FR_ROW = re.compile(r"^\| (FR-\d+) \|")
DEFAULT_REQUIREMENTS = Path("docs/requirements/FUNCTIONAL_REQUIREMENTS.md")
DEFAULT_TEST_ROOTS = (Path("tests/acceptance"), Path("tests/system"))


@dataclass(frozen=True)
class Requirement:
    fr_id: str
    statement: str
    criterion: str
    tier: str


@dataclass(frozen=True)
class AcceptanceTest:
    fr_id: str
    function: str
    path: str
    partly: str


@dataclass(frozen=True)
class Row:
    requirement: Requirement
    tests: tuple[AcceptanceTest, ...]
    result: str
    note: str


def read_requirements(path: Path) -> list[Requirement]:
    """Rows of the functional requirements table: id, statement, acceptance criterion, tier."""
    found: list[Requirement] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not _FR_ROW.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        found.append(Requirement(cells[0], cells[1], cells[-2], cells[-1]))
    return found


def find_tests(roots: Sequence[Path]) -> list[AcceptanceTest]:
    """Test functions (named ``test_*``) whose docstring starts with ``AT-FR-nn``."""
    found: list[AcceptanceTest] = []
    for root in roots:
        for file in sorted(root.rglob("test_*.py")):
            tree = ast.parse(file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue
                if not node.name.startswith("test_"):
                    continue
                doc = ast.get_docstring(node) or ""
                token = _TOKEN.match(doc)
                if token is None:
                    continue
                partly = next(
                    (
                        line.split(":", 1)[1].strip()
                        for line in doc.splitlines()
                        if line.startswith("PARTLY:")
                    ),
                    "",
                )
                found.append(AcceptanceTest(token.group(1), node.name, file.as_posix(), partly))
    return found


def read_results(files: Sequence[Path]) -> dict[str, str]:
    """Function name to ``passed``, ``failed`` or ``skipped`` from JUnit XML files."""
    outcomes: dict[str, str] = {}
    for file in files:
        for case in ElementTree.parse(file).iter("testcase"):
            name = case.get("name", "")
            if case.find("failure") is not None or case.find("error") is not None:
                outcomes[name] = "failed"
            elif case.find("skipped") is not None:
                outcomes.setdefault(name, "skipped")
            else:
                outcomes.setdefault(name, "passed")
    return outcomes


def build_rows(
    requirements: Sequence[Requirement],
    tests: Sequence[AcceptanceTest],
    results: dict[str, str],
) -> list[Row]:
    rows: list[Row] = []
    for requirement in requirements:
        mine = tuple(t for t in tests if t.fr_id == requirement.fr_id)
        if not mine:
            rows.append(Row(requirement, (), "No test", ""))
            continue
        outcomes = [results.get(t.function, "none") for t in mine]
        notes = "; ".join(t.partly for t in mine if t.partly)
        if "failed" in outcomes:
            result = "Not met"
        elif "none" in outcomes:
            result = "No result"
        elif "skipped" in outcomes:
            result = "Skipped"
        else:
            result = "Partly met" if notes else "Met"
        rows.append(Row(requirement, mine, result, notes))
    return rows


def _cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ")


def render(rows: Sequence[Row]) -> str:
    counts = Counter(row.result for row in rows)
    order = ("Met", "Partly met", "Not met", "No result", "Skipped", "No test")
    summary = ", ".join(f"{counts[name]} {name.lower()}" for name in order if counts[name])
    lines = [
        "# Acceptance matrix",
        "",
        "Each functional requirement, its acceptance criterion, the test that checks it and the "
        "result of the last run. The acceptor is the author (ADR-047); one acceptor means no "
        "independent judgement. A test that passes but names something it does not demonstrate "
        "is reported as partly met.",
        "",
        f"**Summary ({len(rows)} requirements):** {summary}.",
        "",
        "| FR | Requirement | Acceptance criterion | Tier | Test | Result | Not demonstrated |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        names = ", ".join(f"`{t.function}`" for t in row.tests) or "-"
        r = row.requirement
        lines.append(
            f"| {r.fr_id} | {_cell(r.statement[:90])} | {_cell(r.criterion)} | {r.tier} | "
            f"{names} | {row.result} | {_cell(row.note) or '-'} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aitaf.quality.acceptance_matrix", description=__doc__)
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--tests", type=Path, action="append", help="folder with acceptance tests")
    parser.add_argument("--junit", type=Path, action="append", default=[], help="JUnit XML file")
    parser.add_argument("--out", type=Path, help="write here instead of printing")
    args = parser.parse_args(argv)
    rows = build_rows(
        read_requirements(args.requirements),
        find_tests(args.tests or list(DEFAULT_TEST_ROOTS)),
        read_results(args.junit),
    )
    text = render(rows)
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}: {sum(1 for r in rows if r.result == 'Met')} met of {len(rows)}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
