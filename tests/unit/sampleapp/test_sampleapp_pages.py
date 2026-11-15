"""Sample shop pages: baseline locators and the committed DOM fixtures.

Requirements: FR-38 (a local application with locators that can be mutated
reproducibly; this file covers the unmutated baseline), NFR-08 (repeatable
rendering), ADR-005 (synthetic content only).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.core.models import LocatorStrategy
from aitaf.healing import find_elements, parse_dom
from aitaf.sampleapp.elements import ELEMENTS, PAGES
from aitaf.sampleapp.pages import render_page

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "dom" / "shop"

ALL_LOCATORS = [(e.name, kind) for e in ELEMENTS.values() for kind in e.kinds]


@pytest.mark.blackbox
@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_a_parseable_document_with_a_title_and_heading(page: str) -> None:
    html = render_page(page)
    assert html.startswith("<!DOCTYPE html>")
    dom = parse_dom(html)
    tags = [e.tag for e in dom.elements]
    assert "title" in tags and "h1" in tags


@pytest.mark.blackbox
@pytest.mark.parametrize(("name", "kind"), ALL_LOCATORS, ids=lambda v: str(v))
def test_every_baseline_locator_finds_exactly_its_element(name: str, kind: str) -> None:
    element = ELEMENTS[name]
    locate = element.locator(kind)
    dom = parse_dom(render_page(element.page))
    found = find_elements(dom, LocatorStrategy(kind=locate.kind, value=locate.value))  # type: ignore[arg-type]
    assert found is not None and len(found) == 1
    assert found[0].tag == element.tag


@pytest.mark.blackbox
def test_there_are_ten_elements_over_five_pages_with_three_or_four_locators_each() -> None:
    assert len(PAGES) == 5
    assert len(ELEMENTS) == 10
    assert {len(e.kinds) for e in ELEMENTS.values()} == {3, 4}
    assert {e.page for e in ELEMENTS.values()} <= set(PAGES)


@pytest.mark.whitebox
def test_text_locators_exist_only_for_elements_with_visible_text() -> None:
    for element in ELEMENTS.values():
        assert ("text" in element.kinds) == bool(element.text)


@pytest.mark.whitebox
@pytest.mark.parametrize("page", PAGES)
def test_rendering_is_deterministic(page: str) -> None:
    assert render_page(page) == render_page(page)


@pytest.mark.whitebox
@pytest.mark.parametrize("page", PAGES)
def test_oracle_mode_only_adds_a_ground_truth_attribute(page: str) -> None:
    baseline = render_page(page)
    oracle = render_page(page, oracle=True)
    assert 'data-gt="' not in baseline
    assert oracle != baseline
    stripped = oracle
    for name in ELEMENTS:
        stripped = stripped.replace(f' data-gt="{name}"', "")
    assert stripped == baseline


@pytest.mark.whitebox
def test_the_cart_page_reflects_the_cart_contents() -> None:
    full = parse_dom(render_page("cart", cart=("backpack",)))
    empty = parse_dom(render_page("cart", cart=()))
    assert any(e.attrs.get("id") == "remove-backpack" for e in full.elements)
    assert not any(e.attrs.get("id") == "remove-backpack" for e in empty.elements)


@pytest.mark.whitebox
def test_unknown_page_is_rejected() -> None:
    with pytest.raises(ValueError):
        render_page("admin")


@pytest.mark.whitebox
def test_error_text_is_escaped() -> None:
    html = render_page("login", error="<script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.blackbox
@pytest.mark.parametrize("page", PAGES)
def test_committed_dom_fixtures_match_the_application(page: str) -> None:
    committed = (FIXTURES / f"{page}.html").read_text(encoding="utf-8")
    assert committed == render_page(page)
