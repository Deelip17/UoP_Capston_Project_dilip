"""Small helpers shared by the LLM package."""

from __future__ import annotations

import hashlib


def input_hash(prompt: str) -> str:
    """SHA-256 of the prompt: the only trace of the input kept in the audit (FR-37)."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
