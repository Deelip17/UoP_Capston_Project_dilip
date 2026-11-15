"""Retry with exponential back-off around any provider (NFR-06).

Only :class:`~aitaf.core.errors.LlmTransientError` is retried; permanent errors
(bad key, bad request) fail at once. After the last attempt the transient error
is re-raised so the gateway can fall back to the mock provider (FR-36) and write
a single audit record for the call (FR-37).
"""

from __future__ import annotations

import time
from collections.abc import Callable

from aitaf.core.errors import LlmTransientError
from aitaf.core.llm.provider import LlmProvider, LlmRequest, LlmResponse
from aitaf.core.logging import get_logger

_log = get_logger(__name__)


class RetryingProvider:
    """Wrap a provider; sleep ``base * 2**n`` seconds (capped) between attempts."""

    def __init__(
        self,
        inner: LlmProvider,
        max_retries: int = 3,
        base_delay_s: float = 1.0,
        max_delay_s: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if base_delay_s < 0:
            raise ValueError("base_delay_s must not be negative")
        if max_delay_s <= 0:
            raise ValueError("max_delay_s must be above zero")
        self._inner = inner
        self._max_retries = max_retries
        self._base = base_delay_s
        self._max_delay = max_delay_s
        self._sleep = sleep
        self.name = inner.name
        self.model: str = getattr(inner, "model", "")

    def complete(self, req: LlmRequest) -> LlmResponse:
        attempt = 0
        while True:
            try:
                return self._inner.complete(req)
            except LlmTransientError as exc:
                if attempt >= self._max_retries:
                    raise
                delay = min(self._max_delay, self._base * 2**attempt)
                attempt += 1
                _log.warning(
                    "transient LLM error, retry %d of %d in %.1f s: %s",
                    attempt,
                    self._max_retries,
                    delay,
                    exc,
                )
                self._sleep(delay)
