"""Render the sample shop pages, with optional mutations (FR-38, NFR-08).

Rendering is a pure function of the page name, the mutation IDs, the cart and an
error message, so the same inputs always give the same HTML. In ``oracle`` mode
every target element also carries ``data-gt="<name>"``: the evaluation harness
uses it to learn which element a test *meant*, without giving that hint to the
healer (the healer is shown the normal rendering).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from html import escape

from aitaf.sampleapp.elements import ELEMENTS, PAGES, Element
from aitaf.sampleapp.mutations import get_mutation

PRODUCTS = {
    "backpack": ("Backpack", "39.00"),
    "lamp": ("Desk Lamp", "24.50"),
    "notebook": ("Notebook", "6.90"),
}

_STYLE = (
    "body{font-family:Arial,sans-serif;max-width:640px;margin:2rem auto;color:#222}"
    "nav{margin-bottom:1rem}.btn{padding:.4rem .9rem;background:#1b5e9b;color:#fff;border:0;"
    "border-radius:4px;cursor:pointer}.field{display:block;margin:.3rem 0 1rem;padding:.4rem;"
    "width:18rem}.error{color:#b00020}li{margin:.6rem 0}"
)


def _attrs(pairs: Iterable[tuple[str, str]]) -> str:
    return "".join(f' {name}="{escape(value, quote=True)}"' for name, value in pairs)


def _element(element: Element, applied: dict[str, set[str]], oracle: bool) -> str:
    """Render one target element with the mutations that apply to it."""
    kinds = applied.get(element.name, set())
    el_id = element.mutated_id if "id" in kinds else element.el_id
    css = element.mutated_class if "class" in kinds else element.css_class
    qa = element.mutated_qa if "xpath" in kinds else element.qa
    text = element.mutated_text if "text" in kinds else element.text
    pairs = [("id", el_id), ("class", f"{element.generic_class} {css}"), ("data-qa", qa)]
    if oracle:
        pairs.append(("data-gt", element.name))
    pairs.extend(element.extra)
    if element.tag == "input":
        html = f"<input{_attrs(pairs)}>"
    else:
        html = f"<{element.tag}{_attrs(pairs)}>{escape(text)}</{element.tag}>"
    if "xpath" in kinds:
        html = f'<div class="layout-box">{html}</div>'
    return html


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>Demo Shop - {escape(title)}</title>\n<style>{_STYLE}</style>\n</head>\n"
        f"<body>\n{body}\n</body>\n</html>\n"
    )


def _login(el: dict[str, str], error: str) -> str:
    message = f'<p id="login-error" class="error">{escape(error)}</p>\n' if error else ""
    return _page(
        "Account access",
        '<h1>Welcome to the Demo Shop</h1>\n<form method="post" action="/login">\n'
        f'<label for="username">Email</label>\n{el["username"]}\n'
        f'<label for="password">Password</label>\n{el["password"]}\n'
        f"{el['login_submit']}\n</form>\n{message}"
        '<p class="hint">Demo account: demo@example.com / demo-pass (synthetic).</p>',
    )


def _products(el: dict[str, str]) -> str:
    items = []
    for sku, (name, price) in PRODUCTS.items():
        if sku == "backpack":
            button = el["add_backpack"]
        else:
            button = (
                f'<button id="add-{sku}" class="btn btn-add-{sku}" data-qa="add-{sku}" '
                f'type="submit">Add {escape(name)} to cart</button>'
            )
        items.append(
            f'<li><span class="name">{escape(name)}</span> <span class="price">${price}</span>\n'
            f'<form method="post" action="/cart/add" style="display:inline">'
            f'<input type="hidden" name="sku" value="{sku}">{button}</form></li>'
        )
    return _page(
        "Catalogue",
        f"<h1>Products</h1>\n<nav>{el['cart_link']}</nav>\n<ul>\n" + "\n".join(items) + "\n</ul>",
    )


def _cart(el: dict[str, str], cart: Sequence[str]) -> str:
    if not cart:
        return _page(
            "Basket",
            '<h1>Your cart</h1>\n<p id="cart-empty">Your cart is empty.</p>\n'
            '<p><a href="/products">Back to products</a></p>',
        )
    rows = []
    for sku in cart:
        name, price = PRODUCTS[sku]
        if sku == "backpack":
            remove = el["remove_item"]
        else:
            remove = (
                f'<button id="remove-{sku}" class="btn btn-remove-{sku}" data-qa="remove-{sku}" '
                f'type="submit">Remove {escape(name)}</button>'
            )
        rows.append(
            f'<li><span class="name">{escape(name)}</span> <span class="price">${price}</span>\n'
            f'<form method="post" action="/cart/remove" style="display:inline">'
            f'<input type="hidden" name="sku" value="{sku}">{remove}</form></li>'
        )
    return _page(
        "Basket",
        "<h1>Your cart</h1>\n<ul>\n" + "\n".join(rows) + "\n</ul>\n"
        f'<form method="get" action="/checkout">{el["checkout_button"]}</form>',
    )


def _checkout(el: dict[str, str]) -> str:
    return _page(
        "Payment",
        '<h1>Checkout</h1>\n<form method="post" action="/checkout">\n'
        '<label for="ship-name">Full name</label>\n'
        f"{el['ship_name']}\n{el['place_order']}\n</form>",
    )


def _confirmation(el: dict[str, str]) -> str:
    return _page(
        "Receipt",
        f"<h1>Order complete</h1>\n{el['confirmation']}\n"
        '<p><a href="/products">Back to products</a></p>',
    )


def render_page(
    page: str,
    mutations: Iterable[str] = (),
    *,
    cart: Sequence[str] = ("backpack",),
    error: str = "",
    oracle: bool = False,
) -> str:
    """Render ``page`` with the given mutations applied.

    Raises :class:`ValueError` for an unknown page and :class:`KeyError` for an
    unknown mutation ID (checked even if the mutation belongs to another page).
    """
    if page not in PAGES:
        raise ValueError(f"unknown page {page!r}; expected one of {', '.join(PAGES)}")
    applied: dict[str, set[str]] = {}
    for mutation_id in mutations:
        mutation = get_mutation(mutation_id)
        applied.setdefault(mutation.element, set()).add(mutation.kind)
    rendered = {
        name: _element(element, applied, oracle)
        for name, element in ELEMENTS.items()
        if element.page == page
    }
    if page == "login":
        return _login(rendered, error)
    if page == "products":
        return _products(rendered)
    if page == "cart":
        return _cart(rendered, cart)
    if page == "checkout":
        return _checkout(rendered)
    return _confirmation(rendered)
