"""Framework exception hierarchy.

All framework errors inherit from :class:`AitafError`, so callers can catch the
whole set with one ``except`` clause. Security-sensitive errors (masking,
validation, policy) "fail closed" (NFR-10, NFR-13, FR-30, FR-15, FR-21).
"""

from __future__ import annotations


class AitafError(Exception):
    """Base class for every framework error."""


class ConfigError(AitafError):
    """Invalid or missing configuration (FR-35, NFR-09)."""


class ValidationError(AitafError):
    """Input or schema validation failed (NFR-10).

    Distinct from :class:`pydantic.ValidationError`; this is raised by code
    outside pydantic (for example by the Data Masking and Validation Layer).
    """


class MaskingError(AitafError):
    """Data masking failed; the caller must fail closed (FR-30, NFR-15)."""


class LlmError(AitafError):
    """Base for LLM Gateway errors (FR-36, FR-37)."""


class LlmTransientError(LlmError):
    """Transient LLM error that may be retried with back-off (NFR-06)."""


class LlmValidationError(LlmError):
    """LLM output failed schema validation (NFR-10)."""


class ExecutionError(AitafError):
    """Test execution could not be carried out or its output was unusable (FR-17)."""


class PersistenceError(AitafError):
    """Storage error, including interrupted runs (NFR-07)."""


class PolicyError(AitafError):
    """A framework policy was violated (host allow-list FR-21, script policy FR-15)."""
