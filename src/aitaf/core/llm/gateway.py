"""The single entry point for every LLM call (FR-36, FR-37, ADR-026).

The gateway enforces the per-run call cap, falls back to a deterministic
provider when the primary one fails (FR-36) and writes exactly one audit record
per call (FR-37, NFR-14). Retry with back-off (NFR-06) is added with the OpenAI
provider; masking (FR-30) is applied by callers before the request is built.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from aitaf.core.errors import LlmError, PolicyError
from aitaf.core.llm.provider import LlmProvider, LlmRequest, LlmResponse
from aitaf.core.llm.util import input_hash
from aitaf.core.logging import current_run_id, get_logger
from aitaf.core.models import LlmAudit
from aitaf.core.storage import Repository

_log = get_logger(__name__)


class LlmGateway:
    """Cap, fallback and audit around an :class:`LlmProvider`."""

    def __init__(
        self,
        provider: LlmProvider,
        repo: Repository,
        call_cap: int,
        fallback: LlmProvider | None = None,
    ) -> None:
        self._provider = provider
        self._repo = repo
        self._call_cap = call_cap
        self._fallback = fallback
        self._calls = 0

    def complete(self, req: LlmRequest) -> LlmResponse:
        run_id = current_run_id()
        if not run_id:
            raise PolicyError("no run ID is set; start a run before calling the LLM gateway")
        if self._calls >= self._call_cap:
            raise PolicyError(f"LLM call cap of {self._call_cap} reached for this run (ADR-026)")
        self._calls += 1

        try:
            response = self._provider.complete(req)
            self._audit(req, run_id, self._provider.name, response, "ok")
            return response
        except LlmError as exc:
            if self._fallback is None:
                self._audit(req, run_id, self._provider.name, None, "error")
                raise
            _log.warning("primary LLM provider failed, using fallback: %s", exc)
            response = self._fallback.complete(req)
            self._audit(req, run_id, self._fallback.name, response, "fallback")
            return response

    def _audit(
        self,
        req: LlmRequest,
        run_id: str,
        provider_name: str,
        response: LlmResponse | None,
        status: Literal["ok", "fallback", "error"],
    ) -> None:
        self._repo.add_audit(
            LlmAudit(
                call_id=uuid.uuid4().hex,
                run_id=run_id,
                component=req.component,
                provider=provider_name,
                model=response.model if response else "none",
                prompt_version=req.prompt_version,
                tokens_in=response.tokens_in if response else 0,
                tokens_out=response.tokens_out if response else 0,
                input_hash=input_hash(req.prompt),
                status=status,
                mock=response.mock if response else False,
                created_at=datetime.now(UTC),
            )
        )
