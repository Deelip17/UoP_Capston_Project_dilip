"""Export and re-import tests.

Requirements: FR-11 (export test cases as JSON, CSV and Markdown and re-import
them with no data loss), NFR-10 (imported files are validated).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.core.errors import ValidationError
from aitaf.core.models import ReviewStatus, TestCase
from aitaf.generator import export_cases, import_cases

AWKWARD = TestCase(
    tc_id="TC-AAAA0001-01",
    req_id="REQ-AAAA0001",
    scenario_id="REQ-AAAA0001-S1",
    title='Login: "quoted", with comma, colon and unicode é中',
    preconditions=["user exists", "- starts with a dash"],
    steps=["open page", 'type "a,b" in the field', "press: submit"],
    expected=["page shows 'welcome', no error"],
    priority="S",
    review_status=ReviewStatus.APPROVED,
    model="mock-1",
    prompt_version="tg-v1",
)
PLAIN = TestCase(
    tc_id="TC-AAAA0001-02",
    req_id="REQ-AAAA0001",
    scenario_id="REQ-AAAA0001-S2",
    title="Reject a bad password",
    steps=["open page", "enter bad password"],
    expected=["error shown"],
    priority="M",
    model="mock-1",
    prompt_version="tg-v1",
)
CASES = [AWKWARD, PLAIN]


@pytest.mark.blackbox
def test_three_export_files_are_produced(tmp_path: Path) -> None:
    paths = export_cases(CASES, tmp_path)
    assert sorted(p.suffix for p in paths) == [".csv", ".json", ".md"]
    assert all(p.exists() and p.stat().st_size > 0 for p in paths)


@pytest.mark.blackbox
@pytest.mark.parametrize("suffix", [".json", ".csv", ".md"])
def test_round_trip_loses_no_data(tmp_path: Path, suffix: str) -> None:
    paths = {p.suffix: p for p in export_cases(CASES, tmp_path)}
    assert import_cases(paths[suffix]) == CASES


@pytest.mark.blackbox
def test_unsupported_import_format_names_supported_ones(tmp_path: Path) -> None:
    path = tmp_path / "cases.xlsx"
    path.write_bytes(b"x")
    with pytest.raises(ValidationError, match=r"\.json"):
        import_cases(path)


@pytest.mark.blackbox
def test_missing_import_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="cannot read"):
        import_cases(tmp_path / "nope.json")


@pytest.mark.whitebox
@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("bad.json", "{not json"),
        ("bad.json", '{"not": "a list"}'),
        ("bad.json", '[{"tc_id": "x"}]'),
        ("bad.csv", "tc_id,title\nx,y\n"),
        ("bad.md", "no headings here"),
        ("bad.md", "## TC-1\ntc_id: TC-1\n"),
    ],
)
def test_malformed_imports_are_rejected_not_half_loaded(
    tmp_path: Path, name: str, content: str
) -> None:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValidationError):
        import_cases(path)


@pytest.mark.whitebox
def test_empty_case_list_exports_and_imports(tmp_path: Path) -> None:
    for path in export_cases([], tmp_path):
        assert import_cases(path) == []
