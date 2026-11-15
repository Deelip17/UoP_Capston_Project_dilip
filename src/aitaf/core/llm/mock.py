"""Deterministic mock provider (FR-36, ADR-026).

Used by default in tests, CI and demos so no network access, key or spend is
needed. A response can be pre-recorded per input hash; otherwise the output is a
fixed JSON document derived from the hash, so identical prompts always give
identical answers. A component can register a deterministic responder so the
pipeline completes offline on fixtures (FR-36).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping

from aitaf.core.llm.provider import LlmRequest, LlmResponse
from aitaf.core.llm.util import input_hash


class MockProvider:
    """Offline provider that never calls a network service."""

    name = "mock"
    model = "mock-1"

    def __init__(
        self,
        recorded: Mapping[str, str] | None = None,
        responders: Mapping[str, Callable[[LlmRequest], str]] | None = None,
    ) -> None:
        self._recorded = dict(recorded or {})
        self._responders = dict(responders or {})

    def complete(self, req: LlmRequest) -> LlmResponse:
        digest = input_hash(req.prompt)
        text = self._recorded.get(digest)
        if text is None and req.component in self._responders:
            text = self._responders[req.component](req)
        if text is None:
            text = json.dumps({"mock": True, "input": digest[:12]})
        return LlmResponse(
            text=text,
            model=self.model,
            tokens_in=len(req.prompt.split()),
            tokens_out=len(text.split()),
            mock=True,
        )
