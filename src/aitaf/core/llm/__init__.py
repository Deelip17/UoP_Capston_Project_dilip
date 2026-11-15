"""LLM Gateway, provider interface, mock provider and provider factory (FR-36, FR-37, NFR-25).

The OpenAI SDK is imported only by ``aitaf.core.llm.openai_provider`` and only when the
live provider is selected.
"""

from aitaf.core.llm.factory import build_providers
from aitaf.core.llm.gateway import LlmGateway
from aitaf.core.llm.mock import MockProvider
from aitaf.core.llm.provider import LlmProvider, LlmRequest, LlmResponse

__all__ = [
    "LlmGateway",
    "LlmProvider",
    "LlmRequest",
    "LlmResponse",
    "MockProvider",
    "build_providers",
]
