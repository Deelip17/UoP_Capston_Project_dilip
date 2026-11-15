"""Documentation rules.

Requirements: NFR-20 (every component package has a README; 100% of packages),
project rule "every module has a package README and docstrings citing FR/NFR IDs".
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[3] / "src" / "aitaf"
PACKAGES = sorted(p.parent for p in SRC.rglob("__init__.py") if "__pycache__" not in p.parts)
TOP_LEVEL = [p for p in PACKAGES if p.parent == SRC]


def name(path: Path) -> str:
    return path.relative_to(SRC).as_posix()


@pytest.mark.blackbox
@pytest.mark.parametrize("package", TOP_LEVEL, ids=name)
def test_every_top_level_package_has_a_readme_citing_requirements(package: Path) -> None:
    readme = package / "README.md"
    assert readme.exists(), f"{name(package)} has no README.md"
    text = readme.read_text(encoding="utf-8")
    assert len(text) > 300
    assert re.search(r"\b(?:N?FR)-\d+", text), "README does not cite any FR or NFR"
    assert "## Not built" in text, "README must say what is not built or not shown"


@pytest.mark.blackbox
def test_the_expected_packages_were_found() -> None:
    assert {name(p) for p in TOP_LEVEL} >= {"core", "analyzer", "generator", "scriptgen", "healing"}


@pytest.mark.whitebox
@pytest.mark.parametrize(
    "module",
    sorted(
        p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts and p.name != "__main__.py"
    ),
    ids=lambda p: p.relative_to(SRC).as_posix(),
)
def test_every_module_has_a_docstring(module: Path) -> None:
    tree = ast.parse(module.read_text(encoding="utf-8"))
    assert ast.get_docstring(tree), f"{module.relative_to(SRC)} has no module docstring"
