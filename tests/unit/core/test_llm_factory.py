"""Provider selection and live-provider settings (FR-35, FR-36, NFR-06, NFR-09, ADR-026).

The default stays the mock provider. The OpenAI provider needs an explicit
opt-in plus the key from the environment; it is wrapped in retry and cache and
always has the mock provider as its fallback.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from aitaf.core.config import Settings
from aitaf.core.errors import ConfigError
from aitaf.core.llm import MockProvider, build_providers
from aitaf.core.llm.cache import CachingProvider
from aitaf.core.llm.retry import RetryingProvider

KEY = "sk-test-DO-NOT-LEAK-1234567890"


def live_settings(**extra: str) -> Settings:
    env = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": KEY, **extra}
    return Settings.from_env(env)


# ---------------------------------------------------------------- settings


@pytest.mark.blackbox
def test_live_provider_settings_have_safe_defaults() -> None:
    settings = Settings.from_env({})
    assert settings.llm_provider == "mock"
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.llm_max_retries == 3
    assert settings.llm_timeout_s == 30.0
    assert settings.llm_cache_dir == ".aitaf_cache/llm"


@pytest.mark.blackbox
def test_live_provider_settings_are_read_from_the_environment() -> None:
    settings = live_settings(
        LLM_MODEL="gpt-test-2", LLM_MAX_RETRIES="5", LLM_TIMEOUT_S="12.5", LLM_CACHE_DIR="cache/x"
    )
    assert settings.llm_model == "gpt-test-2"
    assert settings.llm_max_retries == 5
    assert settings.llm_timeout_s == 12.5
    assert settings.llm_cache_dir == "cache/x"


@pytest.mark.whitebox
def test_empty_cache_dir_turns_the_cache_off() -> None:
    assert live_settings(LLM_CACHE_DIR="").llm_cache_dir is None


@pytest.mark.whitebox
@pytest.mark.parametrize(
    "env",
    [
        {"LLM_MODEL": ""},
        {"LLM_MODEL": "bad model; rm -rf"},
        {"LLM_MAX_RETRIES": "-1"},
        {"LLM_MAX_RETRIES": "11"},
        {"LLM_MAX_RETRIES": "many"},
        {"LLM_TIMEOUT_S": "0"},
        {"LLM_TIMEOUT_S": "301"},
        {"LLM_TIMEOUT_S": "nan"},
        {"LLM_TIMEOUT_S": "soon"},
    ],
)
def test_invalid_live_settings_are_rejected_with_a_clear_message(env: dict[str, str]) -> None:
    with pytest.raises(ConfigError) as info:
        Settings.from_env(env)
    assert next(iter(env)) in str(info.value)


@pytest.mark.whitebox
def test_live_settings_can_come_from_the_configuration_file_but_the_key_cannot() -> None:
    settings = Settings.from_file_data({"llm_model": "gpt-file", "llm_max_retries": 2}, env={})
    assert settings.llm_model == "gpt-file" and settings.llm_max_retries == 2
    with pytest.raises(ConfigError):
        Settings.from_file_data({"openai_api_key": KEY}, env={})


@pytest.mark.blackbox
def test_settings_never_print_the_key() -> None:
    settings = live_settings()
    assert KEY not in repr(settings) and KEY not in str(settings)
    assert KEY not in settings.model_dump_json()


# ----------------------------------------------------------------- factory


@pytest.mark.blackbox
def test_mock_is_the_default_and_has_no_fallback() -> None:
    primary, fallback = build_providers(Settings.from_env({}))
    assert isinstance(primary, MockProvider)
    assert fallback is None


@pytest.mark.blackbox
def test_openai_is_wrapped_in_cache_and_retry_with_a_mock_fallback(tmp_path: Any) -> None:
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace()))
    settings = live_settings(LLM_CACHE_DIR=str(tmp_path))
    primary, fallback = build_providers(settings, openai_client=client)
    assert isinstance(primary, CachingProvider)
    assert primary.name == "openai"
    assert isinstance(fallback, MockProvider)


@pytest.mark.whitebox
def test_without_a_cache_directory_the_provider_is_only_wrapped_in_retry() -> None:
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace()))
    primary, _ = build_providers(live_settings(LLM_CACHE_DIR=""), openai_client=client)
    assert isinstance(primary, RetryingProvider)


@pytest.mark.whitebox
def test_fallback_keeps_the_component_responders() -> None:
    marker = {"requirement_analyzer": lambda req: "from responder"}
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace()))
    _, fallback = build_providers(
        live_settings(LLM_CACHE_DIR=""), responders=marker, openai_client=client
    )
    assert isinstance(fallback, MockProvider)
    from aitaf.core.llm import LlmRequest

    reply = fallback.complete(
        LlmRequest(component="requirement_analyzer", prompt_version="v1", prompt="p")
    )
    assert reply.text == "from responder"


@pytest.mark.whitebox
def test_openai_without_a_key_cannot_be_built() -> None:
    settings = Settings(llm_provider="openai", openai_api_key=None)
    with pytest.raises(ConfigError):
        build_providers(settings)
