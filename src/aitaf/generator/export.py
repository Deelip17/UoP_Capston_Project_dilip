"""Export and re-import of test cases as JSON, CSV and Markdown (FR-11).

All three formats round-trip without loss for cases whose text is single-line
(the generator normalises line breaks). Imports are validated against the
``TestCase`` schema and rejected as a whole if anything is malformed (NFR-10).
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from aitaf.core.errors import ValidationError
from aitaf.core.models import TestCase

FIELDS = list(TestCase.model_fields)
LIST_FIELDS = ("preconditions", "steps", "expected")
SUPPORTED_SUFFIXES = (".json", ".csv", ".md")
_MD_TITLE = "# Test cases"
_MD_KEY = re.compile(r"^([a-z_]+):(?: (.*))?$")


def _to_cases(rows: list[dict[str, Any]], source: str) -> list[TestCase]:
    try:
        return [TestCase.model_validate(row) for row in rows]
    except PydanticValidationError as exc:
        raise ValidationError(f"{source}: invalid test case ({exc.error_count()} errors)") from exc


def _json_text(cases: list[TestCase]) -> str:
    return json.dumps([c.model_dump(mode="json") for c in cases], indent=2, ensure_ascii=False)


def _csv_write(cases: list[TestCase], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for case in cases:
            row = case.model_dump(mode="json")
            for name in LIST_FIELDS:
                row[name] = json.dumps(row[name], ensure_ascii=False)
            writer.writerow(row)


def _md_text(cases: list[TestCase]) -> str:
    lines = [_MD_TITLE, ""]
    for case in cases:
        data = case.model_dump(mode="json")
        lines.append(f"## {case.tc_id}")
        for name in FIELDS:
            if name in LIST_FIELDS:
                lines.append(f"{name}:")
                lines.extend(f"  - {item}" for item in data[name])
            else:
                lines.append(f"{name}: {data[name]}")
        lines.append("")
    return "\n".join(lines)


def export_cases(cases: list[TestCase], directory: Path | str) -> list[Path]:
    """Write ``test_cases.json``, ``.csv`` and ``.md`` into the directory."""
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    json_path, csv_path, md_path = (out / f"test_cases{s}" for s in SUPPORTED_SUFFIXES)
    json_path.write_text(_json_text(cases), encoding="utf-8", newline="\n")
    _csv_write(cases, csv_path)
    md_path.write_text(_md_text(cases), encoding="utf-8", newline="\n")
    return [json_path, csv_path, md_path]


def _import_json(text: str, source: str) -> list[TestCase]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{source}: not valid JSON ({exc.msg})") from exc
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValidationError(f"{source}: expected a JSON list of test case objects")
    return _to_cases(data, source)


def _import_csv(path: Path) -> list[TestCase]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [f for f in FIELDS if f not in (reader.fieldnames or [])]
        if missing:
            raise ValidationError(f"{path.name}: missing columns: {', '.join(missing)}")
        rows: list[dict[str, Any]] = []
        for row in reader:
            parsed: dict[str, Any] = dict(row)
            for name in LIST_FIELDS:
                try:
                    parsed[name] = json.loads(parsed[name])
                except (json.JSONDecodeError, TypeError) as exc:
                    raise ValidationError(f"{path.name}: column {name} is not a JSON list") from exc
            rows.append(parsed)
    return _to_cases(rows, path.name)


def _import_md(text: str, source: str) -> list[TestCase]:
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != _MD_TITLE:
        raise ValidationError(f"{source}: not a test case export (missing '{_MD_TITLE}')")
    rows: list[dict[str, Any]] = []
    current_list: str | None = None
    for line in lines[1:]:
        if line.startswith("## "):
            rows.append({})
            current_list = None
        elif not line.strip():
            continue
        elif not rows:
            raise ValidationError(f"{source}: content before the first test case heading")
        elif line.startswith("  - ") and current_list:
            rows[-1][current_list].append(line[4:])
        else:
            match = _MD_KEY.match(line)
            if not match:
                raise ValidationError(f"{source}: cannot parse line {line!r}")
            key, value = match.group(1), match.group(2) or ""
            if key in LIST_FIELDS:
                rows[-1][key] = []
                current_list = key
            else:
                rows[-1][key] = value
                current_list = None
    return _to_cases(rows, source)


def import_cases(path: Path | str) -> list[TestCase]:
    """Read test cases back from a JSON, CSV or Markdown export."""
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValidationError(
            f"unsupported format {suffix or '(none)'!r}; supported: {', '.join(SUPPORTED_SUFFIXES)}"
        )
    try:
        if suffix == ".csv":
            return _import_csv(file_path)
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValidationError(f"cannot read {file_path.name}: {exc}") from exc
    if suffix == ".json":
        return _import_json(text, file_path.name)
    return _import_md(text, file_path.name)
