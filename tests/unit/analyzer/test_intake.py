"""Requirement intake tests: three formats, one entry point.

Requirements: FR-01 (plain text, Markdown and user-story input from a file path
or as text; unsupported format gives an actionable error), NFR-10.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.analyzer.intake import (
    SUPPORTED_SUFFIXES,
    detect_format,
    load_requirements,
    parse_requirements,
)
from aitaf.core.errors import ValidationError

DATA = Path(__file__).resolve().parents[3] / "data" / "requirements"


@pytest.mark.blackbox
@pytest.mark.parametrize(
    ("name", "expected_count"),
    [("sample_plain.txt", 2), ("sample_user_stories.md", 2), ("sample_requirements.md", 7)],
)
def test_sample_file_in_each_format_is_ingested(name: str, expected_count: int) -> None:
    items = load_requirements(DATA / name)
    assert len(items) == expected_count
    assert all(item.text.strip() for item in items)


@pytest.mark.blackbox
def test_source_refs_name_the_file_and_position() -> None:
    items = load_requirements(DATA / "sample_plain.txt")
    assert [i.source_ref for i in items] == ["sample_plain.txt#1", "sample_plain.txt#2"]


@pytest.mark.blackbox
def test_text_can_be_supplied_directly() -> None:
    items = parse_requirements("The system shall log out idle users.", source_name="cli")
    assert [i.text for i in items] == ["The system shall log out idle users."]


@pytest.mark.blackbox
def test_unsupported_format_error_names_supported_formats(tmp_path: Path) -> None:
    path = tmp_path / "reqs.docx"
    path.write_bytes(b"x")
    with pytest.raises(ValidationError) as info:
        load_requirements(path)
    for suffix in SUPPORTED_SUFFIXES:
        assert suffix in str(info.value)


@pytest.mark.blackbox
def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="cannot read"):
        load_requirements(tmp_path / "nope.md")


@pytest.mark.blackbox
def test_file_that_is_not_utf8_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.txt"
    path.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(ValidationError, match="UTF-8"):
        load_requirements(path)


@pytest.mark.blackbox
def test_empty_file_yields_error(tmp_path: Path) -> None:
    path = tmp_path / "empty.md"
    path.write_text("# only a heading\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="no requirements"):
        load_requirements(path)


@pytest.mark.whitebox
def test_detect_format() -> None:
    assert detect_format("As a user, I want to log in so that I can shop.") == "user_story"
    assert detect_format("# Title\n- one\n- two") == "markdown"
    assert detect_format("Just a sentence.") == "plain"


@pytest.mark.whitebox
def test_bullets_numbers_and_continuation_lines_split_correctly() -> None:
    text = "## Group\n- first item\n  continues here\n2. second item\n\nA loose paragraph."
    texts = [i.text for i in parse_requirements(text, source_name="t")]
    assert texts == ["first item continues here", "second item", "A loose paragraph."]
