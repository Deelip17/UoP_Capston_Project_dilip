"""OpenAI provider behind the gateway (FR-36, NFR-06, NFR-09, NFR-25).

This is the only module that imports the OpenAI SDK (NFR-17). The SDK client is
injectable so tests script every outcome without a network or a key. SDK errors
are translated into the framework hierarchy: rate limits, timeouts, connection
problems and server errors are :class:`~aitaf.core.errors.LlmTransientError`
(retried by :class:`~aitaf.core.llm.retry.RetryingProvider`); everything else is a
permanent :class:`~aitaf.core.errors.LlmError`. Messages name the error class and
status only, never the SDK text, so the API key cannot leak (NFR-09).
"""

from __future__ import annotations

from typing import Any

import openai

from aitaf.core.errors import LlmError, LlmTransientError
from aitaf.core.llm.provider import LlmRequest, LlmResponse


class OpenAIProvider:
    """Chat-completions provider; one user message per request, temperature 0 by default."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_s: float = 30.0,
        client: Any | None = None,
        temperature: float | None = 0.0,
    ) -> None:
        if not api_key.strip():
            raise LlmError("an OpenAI API key is required")
        if not model.strip():
            raise LlmError("an OpenAI model name is required")
        self.model = model
        self._timeout_s = timeout_s
        self._temperature = temperature
        # max_retries=0: retrying is owned by RetryingProvider so it is visible and testable.
        self._client = (
            client if client is not None else openai.OpenAI(api_key=api_key, max_retries=0)
        )

    def __repr__(self) -> str:
        return f"OpenAIProvider(model={self.model!r})"

    def complete(self, req: LlmRequest) -> LlmResponse:
        options: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": req.prompt}],
            "timeout": self._timeout_s,
        }
        if self._temperature is not None:
            options["temperature"] = self._temperature
        try:
            result = self._client.chat.completions.create(**options)
        except openai.OpenAIError as exc:
            raise _translate(exc) from None

        text = (result.choices[0].message.content or "") if result.choices else ""
        if not text.strip():
            raise LlmError("OpenAI returned an empty completion")
        usage = result.usage
        return LlmResponse(
            text=text,
            model=str(result.model or self.model),
            tokens_in=int(usage.prompt_tokens) if usage else 0,
            tokens_out=int(usage.completion_tokens) if usage else 0,
            mock=False,
        )


def _translate(exc: openai.OpenAIError) -> LlmError:
    """Map an SDK error to the framework hierarchy without copying its message."""
    kind = type(exc).__name__
    if isinstance(exc, openai.APIConnectionError | openai.APITimeoutError | openai.RateLimitError):
        return LlmTransientError(f"OpenAI request failed ({kind}); it may be retried")
    if isinstance(exc, openai.APIStatusError):
        if exc.status_code >= 500:
            return LlmTransientError(
                f"OpenAI server error (HTTP {exc.status_code}); it may be retried"
            )
        return LlmError(f"OpenAI rejected the request ({kind}, HTTP {exc.status_code})")
    return LlmError(f"OpenAI request failed ({kind})")
