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

import json
import os
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from aitaf.core.errors import ConfigError

LlmProviderName = Literal["mock", "openai"]
_FILE_KEYS = {
    "llm_provider": "LLM_PROVIDER",
    "llm_call_cap": "LLM_CALL_CAP",
    "log_level": "LOG_LEVEL",
}


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

    @classmethod
    def from_file(cls, path: Path | str, env: dict[str, str] | None = None) -> Settings:
        """Load settings from a JSON configuration file (FR-35)."""
        file_path = Path(path)
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError(
                f"cannot read configuration file {file_path}: {exc.strerror}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"configuration file {file_path} is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigError(f"configuration file {file_path} must contain a JSON object")
        return cls.from_file_data(data, env)

    @classmethod
    def from_file_data(cls, data: dict[str, Any], env: dict[str, str] | None = None) -> Settings:
        """Combine file values with the environment; the environment wins.

        The API key is never accepted from a file (NFR-09).
        """
        if "openai_api_key" in data:
            raise ConfigError("the API key must come from OPENAI_API_KEY, not a configuration file")
        unknown = sorted(set(data) - set(_FILE_KEYS))
        if unknown:
            raise ConfigError(f"unknown configuration keys: {', '.join(unknown)}")
        source = env if env is not None else dict(os.environ)
        merged = {_FILE_KEYS[key]: str(value) for key, value in data.items()}
        for name in (*_FILE_KEYS.values(), "OPENAI_API_KEY"):
            if name in source:
                merged[name] = source[name]
        return cls.from_env(merged)
