"""The failure corpus recipes (FR-27, FR-28, objective O4).

The real-browser build is an integration test; these tests check what can be checked
without a browser: enough distinct tests, valid Python, numbered names, no category given away.
"""

from __future__ import annotations

import ast
import re

import pytest

from aitaf.evaluation.corpus import MIN_FAILURES, corpus_sources


@pytest.mark.blackbox
def test_there_are_enough_distinct_recipes_to_reach_forty_failures() -> None:
    sources = corpus_sources()
    assert len(sources) >= MIN_FAILURES + 5  # some may pass by accident
    bodies = {s.split(":\n", 1)[1] for s in sources}
    assert len(bodies) == len(sources)


@pytest.mark.whitebox
def test_every_recipe_is_valid_python_with_a_numbered_test_function() -> None:
    for number, source in enumerate(corpus_sources(), start=1):
        tree = ast.parse(source)
        names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert names == [f"test_case_{number:03d}"]


@pytest.mark.blackbox
def test_test_names_do_not_reveal_a_category() -> None:
    words = re.compile(r"locator|assert|timing|timeout|environment|data|flaky", re.I)
    for source in corpus_sources():
        header = re.search(r"def (test_\w+)", source)
        assert header and not words.search(header.group(1))


@pytest.mark.blackbox
def test_local_user_paths_are_removed_before_a_corpus_is_stored() -> None:
    from aitaf.evaluation.corpus import scrub

    text = r"File C:\Users\someone\AppData\Local\Temp\x.py and c:/Users/someone/repo/y.py"
    assert "someone" not in scrub(text) and "<user>" in scrub(text)
    assert scrub("net::ERR_CONNECTION_REFUSED at http://127.0.0.1:1/") == (
        "net::ERR_CONNECTION_REFUSED at http://127.0.0.1:1/"
    )


@pytest.mark.blackbox
def test_the_holdout_set_is_a_different_set_of_valid_tests() -> None:
    dev, holdout = corpus_sources("dev"), corpus_sources("holdout")
    assert len(holdout) >= MIN_FAILURES + 5
    assert not {s.split(":\n", 1)[1] for s in dev} & {s.split(":\n", 1)[1] for s in holdout}
    for number, source in enumerate(holdout, start=1):
        assert f"def test_case_{number:03d}(" in source
        ast.parse(source)
    with pytest.raises(ValueError):
        corpus_sources("other")
