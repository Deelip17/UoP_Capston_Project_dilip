"""Automated import-rule check (NFR-17).

Rules, checked statically on every source file:

* a component package (analyzer, generator, scriptgen, healing, ...) may import
  ``aitaf.core`` and itself, never another component's internals;
* ``core`` may not import any component;
* top-level modules (``cli``, ``__main__``) and the ``evaluation`` tool package may wire
  components together;
* only ``core/llm`` imports the OpenAI SDK, only ``core/storage`` imports the
  database driver, and only the Execution Engine package imports Playwright or
  Selenium;
* relative imports may not climb out of their package.

Run ``python -m aitaf.quality.import_rules [ROOT]``; exit code 1 on any violation.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

CORE = "core"
EXEMPT_PACKAGES = frozenset({"quality"})
# tools that run the components against each other, like cli.py: they may import any
# component, but the vendor-library rules still apply to them
WIRING_PACKAGES = frozenset({"evaluation", "dashboard"})
VENDOR_OWNERS: dict[str, tuple[str, ...]] = {
    "openai": ("core", "llm"),
    "sqlite3": ("core", "storage"),
    "playwright": ("execution",),
    "selenium": ("execution",),
}


@dataclass(frozen=True, order=True)
class Violation:
    """One forbidden import with its location."""

    file: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.message}"


def _imported_modules(node: ast.AST) -> list[tuple[str, int]]:
    """(module path, relative level) pairs for an import node; empty for other nodes."""
    if isinstance(node, ast.Import):
        return [(alias.name, 0) for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if node.level == 0 and module == "aitaf":
            return [(f"aitaf.{alias.name}", 0) for alias in node.names]
        return [(module, node.level)]
    return []


def _check_file(rel: Path, tree: ast.AST) -> list[Violation]:
    parts = rel.parts[:-1]
    top = parts[0] if parts and parts[0] not in WIRING_PACKAGES else None
    name = rel.as_posix()
    found: list[Violation] = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        for module, level in _imported_modules(node):
            if level >= 2:
                found.append(Violation(name, line, "relative import climbs out of its package"))
                continue
            if level == 1:
                continue
            first, _, rest = module.partition(".")
            if (
                first in VENDOR_OWNERS
                and parts[: len(VENDOR_OWNERS[first])] != VENDOR_OWNERS[first]
            ):
                owner = "/".join(VENDOR_OWNERS[first])
                found.append(Violation(name, line, f"'{first}' may only be imported under {owner}"))
            if first != "aitaf" or top is None:
                continue
            target = rest.split(".")[0] if rest else ""
            if not target or target == top == CORE:
                continue
            if top == CORE:
                found.append(
                    Violation(name, line, f"core must not import component '{target}' (NFR-17)")
                )
            elif target not in (top, CORE):
                found.append(
                    Violation(
                        name,
                        line,
                        f"component '{top}' must not import component '{target}' (NFR-17)",
                    )
                )
    return found


def check_tree(root: Path) -> list[Violation]:
    """All forbidden imports under ``root`` (the ``aitaf`` package directory)."""
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if rel.parts[0] in EXEMPT_PACKAGES:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            violations.append(
                Violation(rel.as_posix(), exc.lineno or 0, f"syntax error: {exc.msg}")
            )
            continue
        violations.extend(_check_file(rel, tree))
    return sorted(violations)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aitaf.quality.import_rules", description=__doc__)
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"import rules: {root} is not a directory", file=sys.stderr)
        return 2
    violations = check_tree(root)
    for violation in violations:
        print(violation)
    count = len(violations)
    print(f"import rules: {count} forbidden import{'s' if count != 1 else ''}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
