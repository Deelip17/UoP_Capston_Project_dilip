"""Deliberately failing test used only to demonstrate that the pipeline catches defects (evidence E03b)."""


def test_deliberate_failure() -> None:
    assert False, "Deliberate failure to demonstrate the CI pipeline (E03b)"
