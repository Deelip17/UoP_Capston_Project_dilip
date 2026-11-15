"""Choose the LLM provider chain from the settings (FR-35, FR-36, NFR-06, ADR-026).

``mock`` (the default) needs nothing. ``openai`` builds cache over retry over the
OpenAI provider and returns the mock provider, with the same component
responders, as the fallback, so a failed live call still completes offline.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from aitaf.core.config import Settings
from aitaf.core.errors import ConfigError
from aitaf.core.llm.cache import CachingProvider
from aitaf.core.llm.mock import MockProvider
from aitaf.core.llm.provider import LlmProvider, LlmRequest
from aitaf.core.llm.retry import RetryingProvider


def build_providers(
    settings: Settings,
    responders: Mapping[str, Callable[[LlmRequest], str]] | None = None,
    openai_client: Any | None = None,
) -> tuple[LlmProvider, LlmProvider | None]:
    """Return ``(primary, fallback)``; ``fallback`` is None for the mock provider."""
    mock = MockProvider(responders=responders)
    if settings.llm_provider == "mock":
        return mock, None

    if settings.openai_api_key is None:
        raise ConfigError("LLM_PROVIDER=openai requires OPENAI_API_KEY in the environment")
    from aitaf.core.llm.openai_provider import OpenAIProvider  # imported only when live

    live: LlmProvider = OpenAIProvider(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.llm_model,
        timeout_s=settings.llm_timeout_s,
        client=openai_client,
    )
    live = RetryingProvider(live, max_retries=settings.llm_max_retries)
    if settings.llm_cache_dir:
        live = CachingProvider(live, Path(settings.llm_cache_dir))
    return live, mock
