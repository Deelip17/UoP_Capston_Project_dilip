"""Structured logging with a run identifier on every line.

The run identifier propagates through all loggers through a context variable,
so a subsystem does not have to pass it explicitly. The JSON formatter writes a
one-line record with ``ts``, ``level``, ``logger``, ``run_id`` and ``msg``;
``run_id`` is an empty string before any run is set, so it is always present
(NFR-34 acceptance criterion: "run_id present on 100% of log lines").
"""

from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_run_id_var: ContextVar[str] = ContextVar("aitaf_run_id", default="")


def new_run_id() -> str:
    """Return a unique lowercase hexadecimal run identifier."""
    return uuid.uuid4().hex


def set_run_id(run_id: str) -> None:
    """Bind a run identifier to the current context; may be called once per run."""
    _run_id_var.set(run_id)


def current_run_id() -> str:
    """Return the run identifier currently bound, or an empty string."""
    return _run_id_var.get()


class _JsonFormatter(logging.Formatter):
    """One-line JSON formatter that always emits ``run_id``."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "run_id": current_run_id(),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_root(level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger (idempotent).

    Repeated calls replace the handler so test and production configurations
    never overlap.
    """
    root = logging.getLogger()
    root.setLevel(level)
    for existing in list(root.handlers):
        root.removeHandler(existing)
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger.

    The run identifier is attached by the formatter through a context variable,
    so callers never need to pass it; use :func:`set_run_id` once per run.
    """
    return logging.getLogger(name)
