"""Unit tests for Settings and from_env (FR-35, NFR-09, ADR-026, ADR-032)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from aitaf.core.config import Settings
from aitaf.core.errors import ConfigError


@pytest.mark.blackbox
def test_defaults_use_mock_provider() -> None:
    """ADR-026: the mock provider is the default and no API key is required."""
    s = Settings.from_env(env={})
    assert s.llm_provider == "mock"
    assert s.openai_api_key is None
    assert s.llm_call_cap == 100


@pytest.mark.blackbox
def test_openai_requires_api_key() -> None:
    """NFR-09: the openai provider without the env key must fail closed."""
    with pytest.raises(ConfigError):
        Settings.from_env(env={"LLM_PROVIDER": "openai"})


@pytest.mark.blackbox
def test_openai_with_api_key_accepted() -> None:
    s = Settings.from_env(env={"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test-xyz"})
    assert s.llm_provider == "openai"
    assert s.openai_api_key is not None
    assert s.openai_api_key.get_secret_value() == "sk-test-xyz"


@pytest.mark.blackbox
def test_unknown_provider_rejected() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env(env={"LLM_PROVIDER": "anthropic"})


@pytest.mark.whitebox
def test_call_cap_must_be_integer() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env(env={"LLM_CALL_CAP": "not-a-number"})


@pytest.mark.whitebox
def test_call_cap_rejects_negative() -> None:
    """Pydantic field constraint ge=0 on the model."""
    with pytest.raises(PydanticValidationError):
        Settings(llm_call_cap=-1)


@pytest.mark.blackbox
def test_settings_are_immutable() -> None:
    """ConfigDict frozen=True: assignment after construction must raise."""
    s = Settings.from_env(env={})
    with pytest.raises(PydanticValidationError):
        s.llm_provider = "openai"  # type: ignore[misc]


@pytest.mark.whitebox
def test_secret_is_not_in_repr() -> None:
    """NFR-09: the api key must not appear in str or repr output."""
    s = Settings.from_env(env={"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-abc-123"})
    assert "sk-abc-123" not in repr(s)
    assert "sk-abc-123" not in str(s)


@pytest.mark.whitebox
def test_from_env_ignores_unlisted_env_vars() -> None:
    """NFR-09: only the named variables are read; nothing else leaks in."""
    s = Settings.from_env(env={"UNRELATED": "value", "LLM_CALL_CAP": "50"})
    assert s.llm_call_cap == 50
    assert s.llm_provider == "mock"


@pytest.mark.blackbox
def test_prices_default_to_zero_so_mock_runs_cost_nothing() -> None:
    settings = Settings.from_env({})
    assert settings.llm_price_in_per_1k == 0.0 and settings.llm_price_out_per_1k == 0.0


@pytest.mark.blackbox
def test_prices_are_read_from_the_environment() -> None:
    settings = Settings.from_env({"LLM_PRICE_IN_PER_1K": "0.25", "LLM_PRICE_OUT_PER_1K": "1.5"})
    assert (settings.llm_price_in_per_1k, settings.llm_price_out_per_1k) == (0.25, 1.5)


@pytest.mark.blackbox
@pytest.mark.parametrize("bad", ["abc", "-1", "nan", "inf"])
def test_invalid_prices_are_rejected(bad: str) -> None:
    with pytest.raises(ConfigError, match="LLM_PRICE_IN_PER_1K"):
        Settings.from_env({"LLM_PRICE_IN_PER_1K": bad})


@pytest.mark.whitebox
def test_prices_can_come_from_a_config_file_and_the_environment_wins() -> None:
    from_file = Settings.from_file_data({"llm_price_in_per_1k": 0.4}, env={})
    assert from_file.llm_price_in_per_1k == 0.4
    overridden = Settings.from_file_data(
        {"llm_price_in_per_1k": 0.4}, env={"LLM_PRICE_IN_PER_1K": "0.9"}
    )
    assert overridden.llm_price_in_per_1k == 0.9
