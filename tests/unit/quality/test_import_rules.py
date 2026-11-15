"""Automated import-rule check.

Requirements: NFR-17 (components depend on `core` interfaces, not on one another's
internals; an automated check reports zero forbidden imports in CI), plus the
project rules that only `core/llm` imports the OpenAI SDK and only `core/storage`
touches the database driver.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.quality.import_rules import check_tree, main

SRC = Path(__file__).resolve().parents[3] / "src" / "aitaf"


def build(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "aitaf"
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def messages(root: Path) -> list[str]:
    return [v.message for v in check_tree(root)]


@pytest.mark.blackbox
def test_the_real_source_tree_has_zero_forbidden_imports() -> None:
    assert [str(v) for v in check_tree(SRC)] == []


@pytest.mark.blackbox
def test_a_component_may_import_core_and_itself(tmp_path: Path) -> None:
    root = build(
        tmp_path,
        {
            "analyzer/a.py": "from aitaf.core.models import Run\nfrom aitaf.analyzer.b import x\n",
            "analyzer/b.py": "x = 1\n",
            "core/models.py": "import json\n",
        },
    )
    assert check_tree(root) == []


@pytest.mark.blackbox
def test_a_component_importing_another_components_internals_is_reported(tmp_path: Path) -> None:
    root = build(
        tmp_path,
        {
            "analyzer/a.py": "x = 1\nfrom aitaf.generator.generator import TestCaseGenerator\n",
            "generator/generator.py": "class TestCaseGenerator: ...\n",
        },
    )
    (violation,) = check_tree(root)
    assert violation.line == 2
    assert "analyzer" in violation.message and "generator" in violation.message
    assert str(violation).startswith("analyzer")


@pytest.mark.blackbox
def test_import_statement_form_is_caught_too(tmp_path: Path) -> None:
    root = build(tmp_path, {"healing/h.py": "import aitaf.scriptgen.templates\n"})
    assert len(check_tree(root)) == 1


@pytest.mark.blackbox
def test_core_must_not_import_components(tmp_path: Path) -> None:
    root = build(tmp_path, {"core/x.py": "from aitaf.healing import SelfHealingEngine\n"})
    assert "core" in messages(root)[0] and "healing" in messages(root)[0]


@pytest.mark.blackbox
def test_top_level_modules_and_tooling_may_wire_components_together(tmp_path: Path) -> None:
    root = build(
        tmp_path,
        {
            "cli.py": "from aitaf.analyzer import A\nfrom aitaf.healing import B\n",
            "__main__.py": "from aitaf.cli import main\n",
            "quality/tool.py": "from aitaf.core.errors import AitafError\n",
        },
    )
    assert check_tree(root) == []


@pytest.mark.blackbox
@pytest.mark.parametrize(
    ("module", "allowed_in", "forbidden_in"),
    [
        ("openai", "core/llm/p.py", "analyzer/p.py"),
        ("sqlite3", "core/storage/s.py", "generator/s.py"),
        ("playwright", "execution/d.py", "healing/d.py"),
        ("selenium", "execution/d.py", "scriptgen/d.py"),
    ],
)
def test_vendor_imports_are_confined_to_their_owner(
    tmp_path: Path, module: str, allowed_in: str, forbidden_in: str
) -> None:
    assert check_tree(build(tmp_path / "ok", {allowed_in: f"import {module}\n"})) == []
    found = check_tree(build(tmp_path / "bad", {forbidden_in: f"from {module}.sub import x\n"}))
    assert len(found) == 1 and module in found[0].message


@pytest.mark.whitebox
def test_relative_imports_one_level_up_are_refused_but_same_package_is_fine(
    tmp_path: Path,
) -> None:
    ok = build(tmp_path / "ok", {"analyzer/a.py": "from . import b\nfrom .b import x\n"})
    assert check_tree(ok) == []
    bad = build(tmp_path / "bad", {"analyzer/a.py": "from ..core import models\n"})
    assert "relative" in messages(bad)[0]


@pytest.mark.whitebox
def test_a_file_that_does_not_parse_is_reported_not_skipped(tmp_path: Path) -> None:
    root = build(tmp_path, {"analyzer/broken.py": "def (:\n"})
    assert "syntax" in messages(root)[0]


@pytest.mark.whitebox
def test_violations_are_sorted_by_file_then_line(tmp_path: Path) -> None:
    root = build(
        tmp_path,
        {
            "healing/z.py": "import aitaf.scriptgen\n",
            "analyzer/a.py": "import json\nimport aitaf.generator\nimport aitaf.healing\n",
        },
    )
    found = check_tree(root)
    assert [(v.file.split("/")[0], v.line) for v in found] == [
        ("analyzer", 2),
        ("analyzer", 3),
        ("healing", 1),
    ]


@pytest.mark.blackbox
def test_command_line_exit_codes_and_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clean = build(tmp_path / "ok", {"core/x.py": "import json\n"})
    assert main([str(clean)]) == 0
    assert "0 forbidden imports" in capsys.readouterr().out
    dirty = build(tmp_path / "bad", {"analyzer/a.py": "import aitaf.generator\n"})
    assert main([str(dirty)]) == 1
    out = capsys.readouterr().out
    assert "analyzer/a.py:1:" in out and "1 forbidden import" in out


@pytest.mark.whitebox
def test_missing_directory_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "nowhere")]) == 2
    assert "not a directory" in capsys.readouterr().err
