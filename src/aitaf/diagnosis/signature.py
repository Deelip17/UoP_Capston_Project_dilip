"""Failure signatures for clustering (FR-29).

Two failures that differ only in numbers, addresses, ids, paths or quoted values get
the same signature and therefore the same cluster ID. The exception type and the
remaining words (for example a locator name) are kept, because they separate causes.
"""

from __future__ import annotations

import hashlib
import re

_STEPS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"https?://\S+"), "<url>"),
    (re.compile(r"[a-z]:\\[^\s'\"]+"), "<path>"),
    (re.compile(r"(?:/[\w.\-]+){2,}"), "<path>"),
    (re.compile(r"'[^']*'|\"[^\"]*\""), "<str>"),
    (re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{6,}\b"), "<hex>"),
    (re.compile(r"\d+"), "<n>"),
)
_MAX = 300


def normalise_text(text: str) -> str:
    """Lowercase ``text`` and replace the parts that change between runs."""
    out = text.lower()
    for pattern, placeholder in _STEPS:
        out = pattern.sub(placeholder, out)
    return " ".join(out.split())[:_MAX]


def cluster_id(error_type: str, error_text: str) -> str:
    """Stable cluster ID ``CL-xxxxxxxx`` for an exception type and its text."""
    material = f"{error_type.strip().lower()}|{normalise_text(error_text)}"
    return "CL-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:8]
