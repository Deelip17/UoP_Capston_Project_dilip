"""Unit tests for the AITAF exception hierarchy."""

from __future__ import annotations

import pytest

from aitaf.core.errors import (
    AitafError,
    ConfigError,
    LlmError,
    LlmTransientError,
    LlmValidationError,
    MaskingError,
    PersistenceError,
    PolicyError,
    ValidationError,
)


@pytest.mark.blackbox
@pytest.mark.parametrize(
    "exc_cls",
    [
        ConfigError,
        ValidationError,
        MaskingError,
        LlmError,
        LlmTransientError,
        LlmValidationError,
        PersistenceError,
        PolicyError,
    ],
)
def test_every_error_inherits_aitaf_error(exc_cls: type[Exception]) -> None:
    """Catching AitafError must catch every framework error (NFR-10)."""
    with pytest.raises(AitafError):
        raise exc_cls("boom")


@pytest.mark.blackbox
def test_llm_subclasses_inherit_from_llm_error() -> None:
    assert issubclass(LlmTransientError, LlmError)
    assert issubclass(LlmValidationError, LlmError)
