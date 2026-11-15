"""Redaction of secrets and personal data before any LLM call (FR-30, NFR-15).

Only synthetic or public data should ever be supplied (ADR-005); masking is the
safety net that runs regardless. Every match is replaced by a placeholder such as
``[EMAIL]`` and only counts are reported, never the removed values.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from aitaf.core.errors import MaskingError

# Order matters: secrets first, then structured personal data, then looser patterns.
_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("SECRET", re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"), "[SECRET]"),
    ("SECRET", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[SECRET]"),
    ("SECRET", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "[SECRET]"),
    ("SECRET", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{10,}"), "Bearer [SECRET]"),
    (
        "SECRET",
        re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)(\s*[:=]\s*)\S+"),
        r"\1\2[SECRET]",
    ),
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[EMAIL]"),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[CARD]"),
    ("ID", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[ID]"),
    (
        "PHONE",
        re.compile(r"(?:\+\d{1,3}[ -]?)?\(?\d{3}\)?[ -]\d{3}[ -]\d{4}\b|\+\d[\d ()-]{8,}\d"),
        "[PHONE]",
    ),
)


@dataclass(frozen=True)
class MaskResult:
    """Masked text plus how many values of each kind were replaced."""

    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def mask(text: str) -> MaskResult:
    """Replace secrets and personal data with placeholders; fail closed on bad input."""
    if not isinstance(text, str):
        raise MaskingError(f"can only mask text, got {type(text).__name__}")
    counts: Counter[str] = Counter()
    for kind, pattern, replacement in _RULES:
        text, n = pattern.subn(replacement, text)
        counts[kind] += n
    return MaskResult(text=text, counts={k: v for k, v in counts.items() if v})
