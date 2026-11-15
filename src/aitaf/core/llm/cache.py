"""On-disk response cache for live providers (ADR-026, NFR-08).

A rerun with the same prompt costs nothing and gives the same answer. Only live
(non-mock) answers are stored. A cache file is named by the SHA-256 of
provider, model, prompt version and prompt, and holds the answer text and token
counts only: the prompt itself is never written to disk (NFR-15). A damaged file
is treated as a miss and rewritten.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from aitaf.core.llm.provider import LlmProvider, LlmRequest, LlmResponse
from aitaf.core.logging import get_logger

_log = get_logger(__name__)


class CachingProvider:
    """Serve repeated requests from ``cache_dir``; call the inner provider on a miss."""

    def __init__(self, inner: LlmProvider, cache_dir: Path | str) -> None:
        self._inner = inner
        self._dir = Path(cache_dir)
        self.name = inner.name
        self.model: str = getattr(inner, "model", "")

    def complete(self, req: LlmRequest) -> LlmResponse:
        path = self._path(req)
        hit = self._read(path)
        if hit is not None:
            return hit
        response = self._inner.complete(req)
        if not response.mock:
            self._write(path, response)
        return response

    def _path(self, req: LlmRequest) -> Path:
        material = "\x1f".join((self._inner.name, self.model, req.prompt_version, req.prompt))
        return self._dir / f"{hashlib.sha256(material.encode('utf-8')).hexdigest()}.json"

    def _read(self, path: Path) -> LlmResponse | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return LlmResponse(
                text=data["text"],
                model=data["model"],
                tokens_in=data["tokens_in"],
                tokens_out=data["tokens_out"],
                mock=False,
                cached=True,
            )
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError):
            _log.warning("ignoring unreadable LLM cache entry %s", path.name)
            return None

    def _write(self, path: Path, response: LlmResponse) -> None:
        payload = {
            "text": response.text,
            "model": response.model,
            "tokens_in": response.tokens_in,
            "tokens_out": response.tokens_out,
        }
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(".tmp")
            temp.write_text(json.dumps(payload), encoding="utf-8")
            os.replace(temp, path)
        except OSError as exc:  # a cache that cannot be written must not fail the call
            _log.warning("could not write LLM cache entry: %s", exc.strerror)
