"""Fixtures for the system tests: one full pipeline run shared by the whole session (ADR-046)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from pipeline_runner import Pipeline, run_pipeline


@pytest.fixture(scope="session")
def run_factory(tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], Pipeline]:
    root = tmp_path_factory.mktemp("system")
    return lambda name: run_pipeline(root, name)


@pytest.fixture(scope="session")
def run_a(run_factory: Callable[[str], Pipeline]) -> Pipeline:
    return run_factory("a")


@pytest.fixture(scope="session")
def run_b(run_factory: Callable[[str], Pipeline]) -> Pipeline:
    return run_factory("b")
