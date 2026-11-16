"""Release tooling and workflow structure.

Requirements: NFR-19 and NFR-12 (checks and audit gate the release), Git strategy
and ADR-033 (annotated version tags; a GitHub Release with notes from the
changelog and an evidence bundle; `release.yml` triggers on any `v*` tag).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import aitaf
from aitaf.core.errors import ConfigError
from aitaf.quality.release import changelog_section, check_version, main

ROOT = Path(__file__).resolve().parents[3]
CHANGELOG = ROOT / "CHANGELOG.md"
SAMPLE = """# Changelog

## [Unreleased]

## [0.5.0] - 2026-11-14

### Added
- Fifth feature.
- Sixth feature.

## [0.1.0] - 2026-11-14

### Added
- First feature.
"""


@pytest.mark.blackbox
def test_notes_are_the_changelog_section_of_the_version() -> None:
    notes = changelog_section(SAMPLE, "0.5.0")
    assert "Fifth feature." in notes and "Sixth feature." in notes
    assert "First feature." not in notes and "## [" not in notes


@pytest.mark.blackbox
def test_a_leading_v_is_accepted() -> None:
    assert changelog_section(SAMPLE, "v0.1.0") == changelog_section(SAMPLE, "0.1.0")


@pytest.mark.blackbox
@pytest.mark.parametrize("version", ["9.9.9", "0.4.0", "Unreleased-ish"])
def test_a_version_without_a_section_is_refused(version: str) -> None:
    with pytest.raises(ConfigError, match="no changelog section"):
        changelog_section(SAMPLE, version)


@pytest.mark.blackbox
def test_an_empty_section_is_refused() -> None:
    with pytest.raises(ConfigError, match="empty"):
        changelog_section("## [0.2.0] - x\n\n## [0.1.0] - y\n- a\n", "0.2.0")


@pytest.mark.blackbox
def test_the_tag_must_match_the_package_version() -> None:
    check_version("v0.5.0", "0.5.0")
    check_version("0.5.0", "0.5.0")
    with pytest.raises(ConfigError, match="does not match"):
        check_version("v0.5.1", "0.5.0")


@pytest.mark.blackbox
def test_the_current_version_has_release_notes_in_the_real_changelog() -> None:
    notes = changelog_section(CHANGELOG.read_text(encoding="utf-8"), aitaf.__version__)
    assert notes.strip()


@pytest.mark.blackbox
def test_the_package_version_is_a_semantic_version() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+(-rc\d+)?", aitaf.__version__)


@pytest.mark.blackbox
def test_command_line_notes_and_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(SAMPLE, encoding="utf-8")
    assert main(["notes", str(path), "v0.5.0"]) == 0
    assert "Fifth feature." in capsys.readouterr().out
    assert main(["notes", str(path), "v7.0.0"]) == 1
    assert "no changelog section" in capsys.readouterr().err
    assert main(["check", f"v{aitaf.__version__}"]) == 0
    assert main(["check", "v99.0.0"]) == 1
    assert "does not match" in capsys.readouterr().err


@pytest.mark.whitebox
def test_missing_changelog_file_is_a_clear_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["notes", str(tmp_path / "nope.md"), "v0.5.0"]) == 1
    assert "cannot read" in capsys.readouterr().err


@pytest.mark.blackbox
def test_release_workflow_triggers_on_version_tags_only() -> None:
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    on_block = text.split("jobs:")[0]
    assert re.search(r'tags:\s*\[\s*"v\*"\s*\]', on_block)
    assert "branches" not in on_block


@pytest.mark.blackbox
def test_release_workflow_has_least_privilege_and_no_third_party_actions() -> None:
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    top = text.split("jobs:")[0]
    assert "contents: read" in top and "contents: write" not in top
    assert text.count("contents: write") == 1
    assert text.index("contents: write") > text.index("\n  release:")
    uses = re.findall(r"uses:\s*([^\s@]+)@", text)
    assert uses and all(u.startswith("actions/") for u in uses)
    assert set(re.findall(r"secrets\.(\w+)", text)) == {"GITHUB_TOKEN"}
    assert "OPENAI" not in text


@pytest.mark.blackbox
def test_release_workflow_verifies_before_publishing() -> None:
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "needs: verify" in text
    for step in (
        "python -m aitaf.quality.release check",
        "python -m aitaf.quality.import_rules",
        "ruff check",
        "mypy src",
        "--cov-fail-under=80",
        "pip-audit",
        "gh release create",
        "--verify-tag",
        "aitaf.quality.release notes",
    ):
        assert step in text, step


@pytest.mark.blackbox
def test_ci_runs_the_import_rule_check() -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "aitaf.quality.import_rules" in text
