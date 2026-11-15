"""Requirement intake: plain text, Markdown and user stories (FR-01).

One entry point splits any of the three formats into individual requirements.
A new requirement starts at a bullet, a numbered item, a user story ("As a ...
I want ...") or after a blank line; headings are skipped and indented lines
continue the previous item.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from aitaf.core.errors import ValidationError

SUPPORTED_SUFFIXES = (".txt", ".md", ".markdown")
MAX_FILE_BYTES = 200_000

_STORY = re.compile(r"^\s*as an? .+?\bi want\b", re.IGNORECASE)
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_HEADING = re.compile(r"^\s*#{1,6}\s")

SourceFormat = Literal["plain", "markdown", "user_story"]


@dataclass(frozen=True)
class RawRequirement:
    """One requirement as written, with a reference back to its source."""

    source_ref: str
    text: str


def detect_format(text: str) -> SourceFormat:
    """Best-effort format label (user stories win, then Markdown markers)."""
    lines = text.splitlines()
    if any(_STORY.match(line) for line in lines):
        return "user_story"
    if any(_HEADING.match(line) or _BULLET.match(line) for line in lines):
        return "markdown"
    return "plain"


def parse_requirements(text: str, source_name: str) -> list[RawRequirement]:
    """Split text in any supported format into requirements."""
    items: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if not line.strip():
            current = None
            continue
        if _HEADING.match(line):
            current = None
            continue
        bullet = _BULLET.match(line)
        starts_item = bool(bullet) or bool(_STORY.match(line))
        if starts_item or current is None:
            current = [bullet.group(1).strip() if bullet else line.strip()]
            items.append(current)
        else:
            current.append(line.strip())
    return [
        RawRequirement(source_ref=f"{source_name}#{n}", text=" ".join(parts))
        for n, parts in enumerate(items, start=1)
    ]


def load_requirements(path: Path | str) -> list[RawRequirement]:
    """Read a requirements file and split it (FR-01, NFR-10)."""
    file_path = Path(path)
    if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValidationError(
            f"unsupported format {file_path.suffix or '(none)'!r}; "
            f"supported formats: {', '.join(SUPPORTED_SUFFIXES)}"
        )
    try:
        data = file_path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read {file_path}: {exc.strerror}") from exc
    if len(data) > MAX_FILE_BYTES:
        raise ValidationError(f"{file_path.name} is larger than {MAX_FILE_BYTES} bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{file_path.name} is not valid UTF-8") from exc
    items = parse_requirements(text, source_name=file_path.name)
    if not items:
        raise ValidationError(f"no requirements found in {file_path.name}")
    return items
