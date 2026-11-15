"""Data Masking and Validation Layer (FR-02, FR-30, NFR-10, NFR-13, NFR-15)."""

from aitaf.core.masking.masking import MaskResult, mask
from aitaf.core.masking.validation import (
    MAX_REQUIREMENT_CHARS,
    find_injection,
    sanitize_requirement_text,
    validate_llm_json,
)

__all__ = [
    "MAX_REQUIREMENT_CHARS",
    "MaskResult",
    "find_injection",
    "mask",
    "sanitize_requirement_text",
    "validate_llm_json",
]
