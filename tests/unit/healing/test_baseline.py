"""Baseline snapshots: where the original element looked like (FR-23, FR-24).

The healer compares candidates with the original element's signature. A directory of
approved baseline snapshots (for example ``data/dom/shop``) lets the signature be
recovered from whichever page the stored locator resolves on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.core.models import Locator, LocatorStrategy
from aitaf.healing import BaselineSnapshots

SHOP = Path(__file__).resolve().parents[3] / "data" / "dom" / "shop"


def locator(kind: str, value: str, *fallbacks: tuple[str, str]) -> Locator:
    return Locator(
        loc_id="login.login_submit",
        page="login",
        name="login_submit",
        primary=LocatorStrategy(kind=kind, value=value),  # type: ignore[arg-type]
        fallbacks=[LocatorStrategy(kind=k, value=v) for k, v in fallbacks],  # type: ignore[arg-type]
        model="test",
        prompt_version="n/a",
    )


@pytest.mark.blackbox
def test_the_signature_is_taken_from_the_page_where_the_locator_resolves() -> None:
    signature = BaselineSnapshots(SHOP).signature_for(locator("id", "login-button"))
    assert signature is not None
    assert signature.tag == "button"
    assert signature.text == "Log in"
    assert signature.attrs["id"] == "login-button"


@pytest.mark.blackbox
def test_a_locator_that_resolves_nowhere_has_no_signature() -> None:
    assert BaselineSnapshots(SHOP).signature_for(locator("id", "no-such-element")) is None


@pytest.mark.whitebox
def test_a_fallback_is_used_when_the_primary_resolves_nowhere() -> None:
    signature = BaselineSnapshots(SHOP).signature_for(
        locator("id", "gone", ("css", "button.btn-place-order"))
    )
    assert signature is not None and signature.text == "Place order"


@pytest.mark.whitebox
def test_an_ambiguous_locator_is_skipped() -> None:
    # "btn" matches many buttons on the products page: never guess which one was meant.
    assert BaselineSnapshots(SHOP).signature_for(locator("css", "button.btn")) is None


@pytest.mark.whitebox
def test_a_missing_directory_or_unreadable_files_give_an_empty_baseline(tmp_path: Path) -> None:
    assert BaselineSnapshots(tmp_path / "nowhere").signature_for(locator("id", "x")) is None
    (tmp_path / "bad.html").write_bytes(b"\xff\xfe not utf-8")
    assert BaselineSnapshots(tmp_path).signature_for(locator("id", "x")) is None


@pytest.mark.whitebox
def test_the_number_of_snapshots_is_reported() -> None:
    assert len(BaselineSnapshots(SHOP)) == 5
