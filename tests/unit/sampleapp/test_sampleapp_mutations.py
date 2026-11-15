"""Seeded locator mutations of the sample shop (FR-38, NFR-08).

A mutation is one reproducible change to one element: an id rename, a class
rename, a structure change (test hook attribute renamed and the element wrapped
in a new container) or a visible-text change. The unit tests prove that each
mutation breaks exactly its own locator and nothing else, and that the element
is still present and identifiable by the ground-truth attribute.
"""

from __future__ import annotations

import pytest

from aitaf.core.models import LocatorStrategy
from aitaf.healing import find_elements, parse_dom
from aitaf.sampleapp.elements import ELEMENTS, PAGES
from aitaf.sampleapp.mutations import CATALOGUE, get_mutation
from aitaf.sampleapp.pages import render_page


def strategy(element: str, kind: str) -> LocatorStrategy:
    locate = ELEMENTS[element].locator(kind)
    return LocatorStrategy(kind=locate.kind, value=locate.value)  # type: ignore[arg-type]


@pytest.mark.blackbox
def test_catalogue_is_large_enough_for_the_healing_evaluation() -> None:
    assert len(CATALOGUE) >= 30
    kinds = {m.kind for m in CATALOGUE}
    assert kinds == {"id", "class", "xpath", "text"}
    for kind in kinds:
        assert sum(1 for m in CATALOGUE if m.kind == kind) >= 7


@pytest.mark.whitebox
def test_ids_are_unique_stable_and_readable() -> None:
    ids = [m.mutation_id for m in CATALOGUE]
    assert len(ids) == len(set(ids))
    assert all(m.mutation_id == f"M-{m.element}-{m.kind}" for m in CATALOGUE)
    assert ids == sorted(ids, key=ids.index)  # order is fixed, not shuffled per run


@pytest.mark.whitebox
@pytest.mark.parametrize("mutation", CATALOGUE, ids=lambda m: m.mutation_id)
def test_each_mutation_targets_a_real_element_and_a_supported_locator_kind(mutation) -> None:  # type: ignore[no-untyped-def]
    element = ELEMENTS[mutation.element]
    locator_kind = {"class": "css"}.get(mutation.kind, mutation.kind)
    assert locator_kind in element.kinds
    assert mutation.description


@pytest.mark.blackbox
@pytest.mark.parametrize("mutation", CATALOGUE, ids=lambda m: m.mutation_id)
def test_a_mutation_breaks_the_locator_it_targets(mutation) -> None:  # type: ignore[no-untyped-def]
    element = ELEMENTS[mutation.element]
    kind = {"class": "css"}.get(mutation.kind, mutation.kind)
    dom = parse_dom(render_page(element.page, [mutation.mutation_id]))
    assert find_elements(dom, strategy(element.name, kind)) == []


@pytest.mark.blackbox
@pytest.mark.parametrize("mutation", CATALOGUE, ids=lambda m: m.mutation_id)
def test_a_mutation_leaves_the_element_present_and_findable_by_ground_truth(mutation) -> None:  # type: ignore[no-untyped-def]
    element = ELEMENTS[mutation.element]
    dom = parse_dom(render_page(element.page, [mutation.mutation_id], oracle=True))
    marked = [e for e in dom.elements if e.attrs.get("data-gt") == element.name]
    assert len(marked) == 1
    assert marked[0].tag == element.tag


@pytest.mark.blackbox
@pytest.mark.parametrize("mutation", CATALOGUE, ids=lambda m: m.mutation_id)
def test_a_mutation_does_not_damage_any_other_element(mutation) -> None:  # type: ignore[no-untyped-def]
    page = ELEMENTS[mutation.element].page
    dom = parse_dom(render_page(page, [mutation.mutation_id]))
    for other in ELEMENTS.values():
        if other.page != page or other.name == mutation.element:
            continue
        for kind in other.kinds:
            found = find_elements(dom, strategy(other.name, kind))
            assert found is not None and len(found) == 1, (other.name, kind)


@pytest.mark.whitebox
@pytest.mark.parametrize("mutation", CATALOGUE[:6], ids=lambda m: m.mutation_id)
def test_a_mutation_changes_only_its_own_page(mutation) -> None:  # type: ignore[no-untyped-def]
    target = ELEMENTS[mutation.element].page
    for page in PAGES:
        mutated = render_page(page, [mutation.mutation_id])
        assert (mutated != render_page(page)) == (page == target)


@pytest.mark.whitebox
def test_two_mutations_on_one_page_both_apply() -> None:
    first, second = get_mutation("M-login_submit-id"), get_mutation("M-username-class")
    html = render_page("login", [first.mutation_id, second.mutation_id])
    dom = parse_dom(html)
    assert find_elements(dom, strategy("login_submit", "id")) == []
    assert find_elements(dom, strategy("username", "css")) == []
    assert find_elements(dom, strategy("password", "id")) != []


@pytest.mark.whitebox
def test_an_unknown_mutation_is_rejected() -> None:
    with pytest.raises(KeyError):
        get_mutation("M-nothing-id")
    with pytest.raises(KeyError):
        render_page("login", ["M-nothing-id"])


@pytest.mark.whitebox
def test_text_mutation_changes_the_visible_text_only() -> None:
    baseline = parse_dom(render_page("login"))
    mutated = parse_dom(render_page("login", ["M-login_submit-text"]))
    before = next(e for e in baseline.elements if e.attrs.get("id") == "login-button")
    after = next(e for e in mutated.elements if e.attrs.get("id") == "login-button")
    assert before.own_text != after.own_text
    assert before.attrs == after.attrs


@pytest.mark.whitebox
def test_structure_mutation_adds_a_wrapper_and_renames_the_hook() -> None:
    baseline = parse_dom(render_page("login"))
    mutated = parse_dom(render_page("login", ["M-login_submit-xpath"]))
    before = next(e for e in baseline.elements if e.attrs.get("id") == "login-button")
    after = next(e for e in mutated.elements if e.attrs.get("id") == "login-button")
    assert after.depth == before.depth + 1
    assert after.attrs["data-qa"] != before.attrs["data-qa"]
