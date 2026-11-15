"""LLM provider interface and request/response records (NFR-25).

Every provider (mock now, OpenAI in a later slice) implements
:class:`LlmProvider`, so providers and models are swappable and share one set of
contract tests. Only this package may import an LLM vendor SDK.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class LlmRequest(BaseModel):
    """A prompt sent through the gateway (already masked by the caller, FR-30)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    component: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    prompt: str = Field(min_length=1)


class LlmResponse(BaseModel):
    """Provider output; ``mock`` is True for deterministic or recorded responses (FR-36).

    ``cached`` is True when a live answer was replayed from the response cache (ADR-026).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1)
    model: str = Field(min_length=1)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    mock: bool
    cached: bool = False


class LlmProvider(Protocol):
    """Contract every provider implements."""

    name: str

    def complete(self, req: LlmRequest) -> LlmResponse:
        """Return a completion or raise an :class:`~aitaf.core.errors.LlmError`."""
