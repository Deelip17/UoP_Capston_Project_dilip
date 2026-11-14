"""Smoke test: the package imports and exposes a version (supports NFR-19, NFR-26)."""

import aitaf


def test_package_exposes_version() -> None:
    assert aitaf.__version__
