"""DOM snapshot parsing and element signatures.

Requirements: FR-22 to FR-24 (healing works on a DOM snapshot), NFR-10 (the
snapshot is untrusted input: size-limited and parsed defensively).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.core.errors import ValidationError
from aitaf.healing import parse_dom, signature_of
from aitaf.healing.dom import MAX_DOM_CHARS, MAX_ELEMENTS

DATA = Path(__file__).resolve().parents[3] / "data" / "dom"


def load(name: str) -> str:
    return (DATA / name).read_text(encoding="utf-8")


@pytest.mark.blackbox
def test_login_page_is_parsed_into_elements() -> None:
    dom = parse_dom(load("login_before.html"))
    tags = [e.tag for e in dom.elements]
    for expected in ("html", "body", "form", "input", "button", "a", "label", "h1"):
        assert expected in tags


@pytest.mark.blackbox
def test_script_and_style_content_is_ignored() -> None:
    dom = parse_dom(load("login_before.html"))
    everything = " ".join(e.text for e in dom.elements)
    assert "do not parse me" not in everything
    assert "color: red" not in everything


@pytest.mark.blackbox
def test_button_attributes_text_and_parent() -> None:
    dom = parse_dom(load("login_before.html"))
    button = next(e for e in dom.elements if e.tag == "button")
    assert button.attrs["id"] == "login-button"
    assert button.attrs["type"] == "submit"
    assert button.own_text == "Sign in"
    assert dom.elements[button.parent].tag == "form"  # type: ignore[index]


@pytest.mark.blackbox
def test_void_elements_do_not_swallow_their_siblings() -> None:
    dom = parse_dom(load("login_before.html"))
    form = next(e for e in dom.elements if e.tag == "form")
    child_tags = [dom.elements[i].tag for i in form.children]
    assert child_tags == ["h1", "label", "input", "label", "input", "button", "a"]


@pytest.mark.blackbox
def test_own_text_and_full_text_differ_for_nested_markup() -> None:
    dom = parse_dom("<button>Go <b>now</b></button>")
    button = next(e for e in dom.elements if e.tag == "button")
    assert button.own_text == "Go"
    assert button.text == "Go now"


@pytest.mark.blackbox
def test_malformed_html_is_parsed_without_error() -> None:
    dom = parse_dom("<div><p>one<p>two</div><span>x</span><b>unclosed")
    assert {"div", "p", "span", "b"} <= {e.tag for e in dom.elements}


@pytest.mark.whitebox
def test_attribute_names_are_lowercased_and_bare_attributes_kept() -> None:
    dom = parse_dom('<INPUT ID="a" Disabled TYPE="Text">')
    el = dom.elements[0]
    assert el.tag == "input"
    assert el.attrs == {"id": "a", "disabled": "", "type": "Text"}


@pytest.mark.whitebox
def test_depth_and_ancestors_follow_nesting() -> None:
    dom = parse_dom("<main><div><form><button>x</button></form></div></main>")
    button = next(e for e in dom.elements if e.tag == "button")
    assert button.depth == 3
    assert [dom.elements[i].tag for i in dom.ancestors(button)] == ["main", "div", "form"]


@pytest.mark.blackbox
def test_oversized_snapshot_is_rejected() -> None:
    with pytest.raises(ValidationError, match="too large"):
        parse_dom("<p>" + "a" * (MAX_DOM_CHARS + 1))


@pytest.mark.blackbox
def test_snapshot_with_too_many_elements_is_rejected() -> None:
    with pytest.raises(ValidationError, match="too many"):
        parse_dom("<i></i>" * (MAX_ELEMENTS + 1))


@pytest.mark.blackbox
def test_signature_of_the_login_button() -> None:
    dom = parse_dom(load("login_before.html"))
    button = next(e for e in dom.elements if e.tag == "button")
    signature = signature_of(dom, button)
    assert signature.tag == "button"
    assert signature.attrs["id"] == "login-button"
    assert signature.text == "Sign in"
    assert signature.ancestors == ("html", "body", "main", "form")
    assert "forgot password?" in signature.neighbours


@pytest.mark.whitebox
def test_non_string_snapshot_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_dom(None)  # type: ignore[arg-type]
