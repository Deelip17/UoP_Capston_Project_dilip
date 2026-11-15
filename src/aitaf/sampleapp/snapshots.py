"""Write DOM snapshots of the sample shop pages (FR-38).

The baseline snapshots in ``data/dom/shop/`` are fixtures for the healing tests
and the evaluation: the same files the Self-Healing Engine receives as a DOM
snapshot, so they can be inspected and diffed.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from aitaf.sampleapp.elements import PAGES
from aitaf.sampleapp.pages import render_page


def write_snapshots(out_dir: Path | str, mutations: Iterable[str] = ()) -> list[Path]:
    """Write one ``<page>.html`` per page into ``out_dir`` and return the paths."""
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    chosen = tuple(mutations)
    written: list[Path] = []
    for page in PAGES:
        path = target / f"{page}.html"
        path.write_text(render_page(page, chosen), encoding="utf-8", newline="\n")
        written.append(path)
    return written
