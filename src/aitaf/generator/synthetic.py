"""Synthetic test data rules (FR-08, ADR-005, NFR-15).

Model-suggested values are kept only if they carry no secret or personal data
after masking (reserved example/test domains are allowed). Anything else is
replaced by a rule-based synthetic value chosen from the field name.
"""

from __future__ import annotations

import re

from aitaf.core.masking import mask

_SYNTHETIC_EMAIL = re.compile(
    r"[\w.+-]+@(?:example\.(?:com|org|net)|[\w-]+\.(?:test|invalid))\b", re.IGNORECASE
)


def is_synthetic_safe(value: str) -> bool:
    """True if the value shows no secret or real personal data."""
    return mask(_SYNTHETIC_EMAIL.sub("synthetic", value)).total == 0


def rule_value(key: str, index: int) -> str:
    """Deterministic synthetic replacement based on the field name."""
    lowered = key.lower()
    if "email" in lowered:
        return f"user{index}@example.test"
    if "phone" in lowered or "tel" in lowered or "mobile" in lowered:
        return "555-0100"
    if "name" in lowered:
        return "Test User"
    if "date" in lowered or "dob" in lowered or "birth" in lowered:
        return "2000-01-01"
    return "synthetic-value"
