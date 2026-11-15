"""Unit tests for structured logging with a run ID (NFR-34)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import pytest

from aitaf.core.logging import configure_root, get_logger, new_run_id, set_run_id


@pytest.fixture
def _reset_logging() -> Iterator[None]:
    """Isolate the root logger between tests."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    yield
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in saved_handlers:
        root.addHandler(h)
    root.setLevel(saved_level)


@pytest.mark.blackbox
def test_new_run_id_is_unique_lowercase_hex() -> None:
    a = new_run_id()
    b = new_run_id()
    assert a != b
    assert len(a) >= 16
    assert all(c in "0123456789abcdef" for c in a)


@pytest.mark.blackbox
def test_log_line_includes_the_run_id(
    capfd: pytest.CaptureFixture[str], _reset_logging: None
) -> None:
    """NFR-34 acceptance: run_id present on 100% of log lines."""
    configure_root("INFO")
    rid = new_run_id()
    set_run_id(rid)
    logger = get_logger("aitaf.test.with_run_id")
    logger.info("hello")
    captured = capfd.readouterr()
    lines = [ln for ln in captured.err.strip().splitlines() if ln]
    payload = json.loads(lines[-1])
    assert payload["run_id"] == rid
    assert payload["msg"] == "hello"
    assert payload["level"] == "INFO"


@pytest.mark.whitebox
def test_log_line_has_empty_run_id_before_any_run(
    capfd: pytest.CaptureFixture[str], _reset_logging: None
) -> None:
    """Even before a run starts, the run_id field exists (empty string)."""
    configure_root("INFO")
    set_run_id("")  # explicit reset for isolation
    logger = get_logger("aitaf.test.no_run")
    logger.info("no-run")
    captured = capfd.readouterr()
    lines = [ln for ln in captured.err.strip().splitlines() if ln]
    payload = json.loads(lines[-1])
    assert payload["run_id"] == ""


@pytest.mark.whitebox
def test_configure_root_is_idempotent(_reset_logging: None) -> None:
    configure_root("INFO")
    configure_root("DEBUG")
    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert root.level == logging.DEBUG
