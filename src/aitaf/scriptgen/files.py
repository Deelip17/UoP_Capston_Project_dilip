"""Confined file writing for generated artefacts (NFR-11)."""

from __future__ import annotations

from pathlib import Path

from aitaf.core.errors import PolicyError


def safe_write(root: Path, relative: str, text: str) -> Path:
    """Write ``text`` under ``root``; refuse any path that resolves outside it."""
    base = root.resolve()
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise PolicyError(f"refusing to write outside the output directory: {relative}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    return target
