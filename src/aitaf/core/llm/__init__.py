"""LLM Gateway, provider interface and mock provider (FR-36, FR-37, NFR-25)."""

from aitaf.core.llm.gateway import LlmGateway
from aitaf.core.llm.mock import MockProvider
from aitaf.core.llm.provider import LlmProvider, LlmRequest, LlmResponse

__all__ = ["LlmGateway", "LlmProvider", "LlmRequest", "LlmResponse", "MockProvider"]
