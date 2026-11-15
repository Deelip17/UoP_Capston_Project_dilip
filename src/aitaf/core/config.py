"""Framework configuration loaded from environment variables.

The configuration object is immutable within a run. Secrets are read from the
environment only and held in :class:`pydantic.SecretStr` so they do not appear
in ``repr``, ``str`` or JSON output (NFR-09). The mock LLM provider is the
default (ADR-026); switching to OpenAI requires both an explicit opt-in and the
``OPENAI_API_KEY`` variable, and even then a per-run call cap limits spending.

Related requirements: FR-35 (configuration file), NFR-09 (secure API key
storage), ADR-026 (budget).
"""

from __future__ import annotations

import os
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from aitaf.core.errors import ConfigError

LlmProviderName = Literal["mock", "openai"]


class Settings(BaseModel):
    """Runtime settings for the framework (frozen after construction)."""

    model_config = ConfigDict(frozen=True)

    llm_provider: LlmProviderName = Field(default="mock")
    openai_api_key: SecretStr | None = Field(default=None)
    llm_call_cap: int = Field(default=100, ge=0)
    log_level: str = Field(default="INFO")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        """Build settings from the environment.

        Only the four variables named below are read; any other environment
        value is ignored. This keeps unrelated secrets out of the framework
        (NFR-09).
        """
        source = env if env is not None else dict(os.environ)
        provider_raw = source.get("LLM_PROVIDER", "mock").lower()
        if provider_raw not in ("mock", "openai"):
            raise ConfigError(f"LLM_PROVIDER must be 'mock' or 'openai', got {provider_raw!r}")
        provider = cast(LlmProviderName, provider_raw)

        key_str = source.get("OPENAI_API_KEY")
        if provider == "openai" and not key_str:
            raise ConfigError("LLM_PROVIDER=openai requires OPENAI_API_KEY in the environment")

        cap_str = source.get("LLM_CALL_CAP", "100")
        try:
            cap = int(cap_str)
        except ValueError as exc:
            raise ConfigError(
                f"LLM_CALL_CAP must be a non-negative integer, got {cap_str!r}"
            ) from exc

        return cls(
            llm_provider=provider,
            openai_api_key=SecretStr(key_str) if key_str else None,
            llm_call_cap=cap,
            log_level=source.get("LOG_LEVEL", "INFO"),
        )
