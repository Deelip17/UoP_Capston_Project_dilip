"""Framework configuration loaded from environment variables.

The configuration object is immutable within a run. Secrets are read from the
environment only and held in :class:`pydantic.SecretStr` so they do not appear
in ``repr``, ``str`` or JSON output (NFR-09). The mock LLM provider is the
default (ADR-026); switching to OpenAI requires both an explicit opt-in and the
``OPENAI_API_KEY`` variable, and even then a per-run call cap limits spending.
The live provider is tuned with ``LLM_MODEL``, ``LLM_MAX_RETRIES`` (NFR-06),
``LLM_TIMEOUT_S`` and ``LLM_CACHE_DIR`` (ADR-026).

Related requirements: FR-35 (configuration file), NFR-09 (secure API key
storage), ADR-026 (budget).
"""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from aitaf.core.errors import ConfigError

LlmProviderName = Literal["mock", "openai"]
_FILE_KEYS = {
    "llm_provider": "LLM_PROVIDER",
    "llm_call_cap": "LLM_CALL_CAP",
    "log_level": "LOG_LEVEL",
    "llm_price_in_per_1k": "LLM_PRICE_IN_PER_1K",
    "llm_price_out_per_1k": "LLM_PRICE_OUT_PER_1K",
    "llm_model": "LLM_MODEL",
    "llm_max_retries": "LLM_MAX_RETRIES",
    "llm_timeout_s": "LLM_TIMEOUT_S",
    "llm_cache_dir": "LLM_CACHE_DIR",
}
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_CACHE_DIR = ".aitaf_cache/llm"
_MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*")


def _price(source: dict[str, str], name: str) -> float:
    raw = source.get(name, "0")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a non-negative number, got {raw!r}") from exc
    if not math.isfinite(value) or value < 0:
        raise ConfigError(f"{name} must be a non-negative number, got {raw!r}")
    return value


def _bounded_int(source: dict[str, str], name: str, default: int, low: int, high: int) -> int:
    raw = source.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer from {low} to {high}, got {raw!r}") from exc
    if not low <= value <= high:
        raise ConfigError(f"{name} must be an integer from {low} to {high}, got {raw!r}")
    return value


def _timeout(source: dict[str, str], name: str, default: float, high: float) -> float:
    raw = source.get(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(
            f"{name} must be a number above 0 and at most {high}, got {raw!r}"
        ) from exc
    if not math.isfinite(value) or not 0 < value <= high:
        raise ConfigError(f"{name} must be a number above 0 and at most {high}, got {raw!r}")
    return value


class Settings(BaseModel):
    """Runtime settings for the framework (frozen after construction)."""

    model_config = ConfigDict(frozen=True)

    llm_provider: LlmProviderName = Field(default="mock")
    openai_api_key: SecretStr | None = Field(default=None)
    llm_call_cap: int = Field(default=100, ge=0)
    log_level: str = Field(default="INFO")
    llm_price_in_per_1k: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    llm_price_out_per_1k: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    llm_model: str = Field(default=DEFAULT_MODEL, min_length=1)
    llm_max_retries: int = Field(default=3, ge=0, le=10)
    llm_timeout_s: float = Field(default=30.0, gt=0.0, le=300.0, allow_inf_nan=False)
    llm_cache_dir: str | None = Field(default=DEFAULT_CACHE_DIR)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        """Build settings from the environment.

        Only the variables named in this module are read; any other environment
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

        prices = {
            name: _price(source, name) for name in ("LLM_PRICE_IN_PER_1K", "LLM_PRICE_OUT_PER_1K")
        }

        model = source.get("LLM_MODEL", DEFAULT_MODEL)
        if not _MODEL_NAME.fullmatch(model):
            raise ConfigError(f"LLM_MODEL must be a model name such as gpt-4o-mini, got {model!r}")
        cache_dir = source.get("LLM_CACHE_DIR", DEFAULT_CACHE_DIR)

        return cls(
            llm_provider=provider,
            openai_api_key=SecretStr(key_str) if key_str else None,
            llm_call_cap=cap,
            log_level=source.get("LOG_LEVEL", "INFO"),
            llm_price_in_per_1k=prices["LLM_PRICE_IN_PER_1K"],
            llm_price_out_per_1k=prices["LLM_PRICE_OUT_PER_1K"],
            llm_model=model,
            llm_max_retries=_bounded_int(source, "LLM_MAX_RETRIES", 3, 0, 10),
            llm_timeout_s=_timeout(source, "LLM_TIMEOUT_S", 30.0, 300.0),
            llm_cache_dir=cache_dir or None,
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
