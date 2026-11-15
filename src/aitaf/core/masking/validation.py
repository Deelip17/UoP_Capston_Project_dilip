"""Input validation and LLM-output validation (FR-02, NFR-10, NFR-13).

Requirement text is untrusted input that ends up inside an LLM prompt, and LLM
output is untrusted too. Input is checked for size, encoding, control characters
and prompt-injection patterns and rejected (fail closed) on failure; output must
parse and match a pydantic schema before anything uses it.
"""

from __future__ import annotations

import json
import re
import unicodedata

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from aitaf.core.errors import LlmValidationError, ValidationError
from aitaf.core.logging import get_logger

MAX_REQUIREMENT_CHARS = 2000

_log = get_logger(__name__)

_INJECTION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "override-instructions",
        re.compile(
            r"(?i)\b(ignore|disregard|forget|override)\b[^.\n]{0,40}"
            r"\b(previous|prior|above|earlier|all|everything)\b"
        ),
    ),
    ("role-hijack", re.compile(r"(?i)\byou are now\b")),
    (
        "prompt-leak",
        re.compile(
            r"(?i)\b(reveal|show|print|output|leak)\b[^.\n]{0,40}"
            r"\b(system prompt|instructions|api key|secret|password)\b"
        ),
    ),
    ("delimiter-spoof", re.compile(r"REQUIREMENT>>>|<<<REQUIREMENT|TEST_CASE>>>|<<<TEST_CASE")),
    (
        "chat-markup",
        re.compile(r"<\|[a-z_]+\|>|^\s*#{1,3}\s*system\b", re.IGNORECASE | re.MULTILINE),
    ),
)


def find_injection(text: str) -> list[str]:
    """Names of the injection rules the text matches."""
    return [name for name, pattern in _INJECTION_RULES if pattern.search(text)]


def _strip_control(text: str) -> str:
    kept = []
    for ch in text.replace("\r\n", "\n").replace("\r", "\n"):
        category = unicodedata.category(ch)
        if ch in "\n\t" or category not in ("Cc", "Cf"):
            kept.append(ch)
    return "".join(kept)


def sanitize_requirement_text(
    text: str | bytes, max_chars: int = MAX_REQUIREMENT_CHARS, source: str = "input"
) -> str:
    """Return clean requirement text or raise :class:`ValidationError` (FR-02).

    Rejections are logged with the source reference and the reason, never the text.
    """
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as exc:
            _log.warning("rejected %s: invalid UTF-8", source)
            raise ValidationError(f"{source}: input is not valid UTF-8") from exc
    cleaned = _strip_control(text).strip()
    if not cleaned:
        _log.warning("rejected %s: empty", source)
        raise ValidationError(f"{source}: input is empty")
    if len(cleaned) > max_chars:
        _log.warning("rejected %s: too long (%d chars)", source, len(cleaned))
        raise ValidationError(f"{source}: input is too long ({len(cleaned)} > {max_chars} chars)")
    matched = find_injection(cleaned)
    if matched:
        _log.warning("rejected %s: prompt-injection pattern %s", source, ",".join(matched))
        raise ValidationError(f"{source}: possible prompt injection ({', '.join(matched)})")
    return cleaned


def validate_llm_json[T: BaseModel](raw: str, model: type[T]) -> T:
    """Parse LLM output as JSON and validate it against ``model`` (NFR-10)."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LlmValidationError(f"LLM output is not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise LlmValidationError("LLM output must be a JSON object")
    try:
        return model.model_validate(data)
    except PydanticValidationError as exc:
        raise LlmValidationError(
            f"LLM output does not match the schema: {exc.error_count()} errors"
        ) from exc
