"""DOM-similarity scoring.

Requirements: FR-23 (second rung: DOM-similarity matching on tag, attributes,
visible text, position in the tree and neighbouring elements).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.core.healing import ElementSignature
from aitaf.healing import WEIGHTS, parse_dom, signature_of, similarity

DATA = Path(__file__).resolve().parents[3] / "data" / "dom"


def dom_of(name: str):  # type: ignore[no-untyped-def]
    return parse_dom((DATA / name).read_text(encoding="utf-8"))


BEFORE = dom_of("login_before.html")
BUTTON = next(e for e in BEFORE.elements if e.tag == "button")
BASELINE = signature_of(BEFORE, BUTTON)


def best(dom, signature=BASELINE):  # type: ignore[no-untyped-def]
    return max(dom.elements, key=lambda e: similarity(signature, dom, e))


@pytest.mark.blackbox
def test_an_element_matches_its_own_signature_perfectly() -> None:
    assert similarity(BASELINE, BEFORE, BUTTON) == pytest.approx(1.0)


@pytest.mark.blackbox
@pytest.mark.parametrize(
    ("page", "new_id"),
    [
        ("login_id_changed.html", "btn-login-9f2"),
        ("login_all_changed.html", "go-4271"),
        ("login_wrapped.html", "submit-9"),
    ],
)
def test_the_mutated_button_is_still_the_best_match(page: str, new_id: str) -> None:
    dom = dom_of(page)
    winner = best(dom)
    assert winner.attrs.get("id") == new_id
    assert similarity(BASELINE, dom, winner) >= 0.6


@pytest.mark.blackbox
def test_unrelated_elements_score_clearly_lower() -> None:
    dom = dom_of("login_all_changed.html")
    winner = best(dom)
    runner_up = sorted(
        (similarity(BASELINE, dom, e) for e in dom.elements if e is not winner), reverse=True
    )[0]
    assert similarity(BASELINE, dom, winner) - runner_up > 0.2


@pytest.mark.blackbox
def test_a_look_alike_button_with_another_label_still_scores_above_threshold() -> None:
    dom = dom_of("login_wrong_element.html")
    winner = best(dom)
    assert winner.attrs["id"] == "cancel-order"
    assert similarity(BASELINE, dom, winner) >= 0.6


@pytest.mark.whitebox
def test_scores_are_always_between_zero_and_one() -> None:
    for page in ("login_before.html", "login_id_changed.html", "login_wrong_element.html"):
        dom = dom_of(page)
        for element in dom.elements:
            assert 0.0 <= similarity(BASELINE, dom, element) <= 1.0


@pytest.mark.whitebox
def test_weights_sum_to_one() -> None:
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


@pytest.mark.whitebox
def test_components_without_expected_data_are_left_out_and_the_rest_renormalised() -> None:
    only_text = ElementSignature(tag=None, attrs={}, text="forgot password?")
    link = next(e for e in BEFORE.elements if e.attrs.get("class") == "forgot")
    assert similarity(only_text, BEFORE, link) == pytest.approx(1.0)
    assert similarity(only_text, BEFORE, BUTTON) < 0.5


@pytest.mark.whitebox
def test_a_signature_with_no_information_scores_zero() -> None:
    empty = ElementSignature(tag=None, attrs={}, text="")
    assert similarity(empty, BEFORE, BUTTON) == 0.0


@pytest.mark.whitebox
def test_tag_only_signature_scores_by_tag() -> None:
    tag_only = ElementSignature(tag="button", attrs={}, text="")
    assert similarity(tag_only, BEFORE, BUTTON) == 1.0
    link = next(e for e in BEFORE.elements if e.tag == "a")
    assert similarity(tag_only, BEFORE, link) == 0.0


@pytest.mark.whitebox
def test_class_tokens_count_individually() -> None:
    expected = ElementSignature(tag=None, attrs={"class": "btn btn-primary"}, text="")
    same = parse_dom('<button class="btn btn-primary">x</button>')
    half = parse_dom('<button class="btn other">x</button>')
    none = parse_dom('<button class="zzz">x</button>')
    assert similarity(expected, same, same.elements[0]) == 1.0
    assert 0.0 < similarity(expected, half, half.elements[0]) < 1.0
    assert similarity(expected, none, none.elements[0]) == 0.0


@pytest.mark.whitebox
def test_ancestor_path_difference_lowers_the_context_score() -> None:
    same_place = parse_dom("<main><form><button>Go</button></form></main>")
    elsewhere = parse_dom("<footer><div><span><button>Go</button></span></div></footer>")
    expected = signature_of(same_place, same_place.elements[2])
    near = similarity(expected, same_place, same_place.elements[2])
    far = similarity(expected, elsewhere, elsewhere.elements[3])
    assert near > far


@pytest.mark.whitebox
def test_neighbours_missing_from_the_candidate_score_zero_for_that_part() -> None:
    expected = ElementSignature(tag=None, attrs={}, text="", neighbours=("forgot password?",))
    lonely = parse_dom("<form><button>Go</button></form>")
    assert similarity(expected, lonely, lonely.elements[1]) == 0.0
