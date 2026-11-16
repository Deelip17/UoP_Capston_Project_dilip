"""The local sample shop server (FR-38, FR-21, NFR-11, ADR-005).

Black-box tests drive the real HTTP server on a free local port with the standard
library only. The server must bind to the loopback address (so it can sit on the
Execution Engine's host allow-list and is never reachable from outside), use
synthetic credentials, and serve whichever mutations it was started with.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator

import pytest

from aitaf.healing import parse_dom
from aitaf.sampleapp.server import DEMO_PASSWORD, DEMO_USER, ShopServer


def get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def post(url: str, data: dict[str, str]) -> tuple[int, str]:
    body = urllib.parse.urlencode(data).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def ids_of(html: str) -> set[str]:
    return {e.attrs["id"] for e in parse_dom(html).elements if "id" in e.attrs}


@pytest.fixture
def shop() -> Iterator[ShopServer]:
    with ShopServer() as server:
        yield server


def log_in(shop: ShopServer) -> None:
    post(f"{shop.url}/login", {"username": DEMO_USER, "password": DEMO_PASSWORD})


@pytest.mark.blackbox
def test_server_binds_to_the_loopback_address_on_a_free_port(shop: ShopServer) -> None:
    assert shop.url.startswith("http://127.0.0.1:")
    assert shop.port > 0


@pytest.mark.blackbox
def test_login_page_is_served_and_the_root_leads_to_it(shop: ShopServer) -> None:
    status, html = get(f"{shop.url}/")
    assert status == 200 and "login-button" in ids_of(html)


@pytest.mark.blackbox
def test_correct_credentials_lead_to_the_product_list(shop: ShopServer) -> None:
    status, html = post(f"{shop.url}/login", {"username": DEMO_USER, "password": DEMO_PASSWORD})
    assert status == 200
    assert "add-backpack" in ids_of(html)


@pytest.mark.blackbox
def test_wrong_credentials_show_an_error_and_keep_products_closed(shop: ShopServer) -> None:
    status, html = post(f"{shop.url}/login", {"username": DEMO_USER, "password": "wrong"})
    assert status == 200 and "login-error" in ids_of(html)
    _, products = get(f"{shop.url}/products")
    assert "login-button" in ids_of(products)  # redirected back to the login page


@pytest.mark.blackbox
def test_shopping_journey_from_cart_to_confirmation(shop: ShopServer) -> None:
    log_in(shop)
    post(f"{shop.url}/cart/add", {"sku": "backpack"})
    _, cart = get(f"{shop.url}/cart")
    assert "remove-backpack" in ids_of(cart) and "checkout-button" in ids_of(cart)
    status, confirmation = post(f"{shop.url}/checkout", {"name": "Test Customer"})
    assert status == 200 and "confirmation" in ids_of(confirmation)
    _, after = get(f"{shop.url}/cart")
    assert "remove-backpack" not in ids_of(after)


@pytest.mark.blackbox
def test_removing_an_item_empties_the_cart(shop: ShopServer) -> None:
    log_in(shop)
    post(f"{shop.url}/cart/add", {"sku": "backpack"})
    post(f"{shop.url}/cart/remove", {"sku": "backpack"})
    _, cart = get(f"{shop.url}/cart")
    assert "remove-backpack" not in ids_of(cart)


@pytest.mark.blackbox
def test_checkout_without_a_name_is_refused(shop: ShopServer) -> None:
    log_in(shop)
    post(f"{shop.url}/cart/add", {"sku": "backpack"})
    status, _ = post(f"{shop.url}/checkout", {"name": "  "})
    assert status == 400


@pytest.mark.blackbox
def test_checkout_with_an_empty_cart_is_refused(shop: ShopServer) -> None:
    log_in(shop)
    status, _ = post(f"{shop.url}/checkout", {"name": "Test Customer"})
    assert status == 400


@pytest.mark.whitebox
def test_unknown_product_and_unknown_route_are_rejected(shop: ShopServer) -> None:
    log_in(shop)
    assert post(f"{shop.url}/cart/add", {"sku": "../../etc/passwd"})[0] == 400
    assert get(f"{shop.url}/admin")[0] == 404


@pytest.mark.whitebox
def test_pages_that_need_a_login_redirect_to_the_login_page(shop: ShopServer) -> None:
    for path in ("/products", "/cart", "/checkout"):
        _, html = get(f"{shop.url}{path}")
        assert "login-button" in ids_of(html), path


@pytest.mark.blackbox
def test_server_serves_the_mutations_it_was_started_with() -> None:
    with ShopServer(mutations=["M-login_submit-id"]) as shop:
        _, html = get(f"{shop.url}/login")
    found = ids_of(html)
    assert "login-button" not in found and "signin-btn" in found


@pytest.mark.whitebox
def test_unknown_mutation_is_rejected_before_the_server_starts() -> None:
    with pytest.raises(KeyError):
        ShopServer(mutations=["M-nothing-id"])


@pytest.mark.whitebox
def test_server_stops_and_releases_the_port() -> None:
    with ShopServer() as shop:
        url = shop.url
    with pytest.raises(urllib.error.URLError):
        get(f"{url}/login")


@pytest.mark.whitebox
def test_demo_credentials_are_synthetic() -> None:
    assert DEMO_USER.endswith("@example.com")


@pytest.mark.blackbox
def test_open_login_mode_accepts_any_credentials_and_opens_the_products_page() -> None:
    with ShopServer(open_login=True) as shop:
        status, html = get(f"{shop.url}/products")  # no login needed
        assert status == 200 and "add-backpack" in ids_of(html)
        _, after = post(f"{shop.url}/login", {"username": "anyone", "password": "x"})
        assert "add-backpack" in ids_of(after)


@pytest.mark.blackbox
def test_default_mode_still_refuses_wrong_credentials() -> None:
    with ShopServer() as shop:
        _, html = post(f"{shop.url}/login", {"username": "anyone", "password": "x"})
        assert "Invalid email or password" in html
        _, products = get(f"{shop.url}/products")
        assert "add-backpack" not in ids_of(products)
