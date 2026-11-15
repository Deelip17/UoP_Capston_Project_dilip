"""The ten target elements of the sample shop and their four locators (FR-38).

Each element has an id, a class, a test-hook attribute (``data-qa``, used by an
XPath) and, if it shows text, a visible text. The mutation catalogue changes one
of these per mutation; ``mutated_*`` hold the replacement values, chosen to look
like a realistic refactor rather than random noise.

This module is plain data: it imports nothing from the framework, so the
application under test stays independent of the system that tests it.
"""

from __future__ import annotations

from dataclasses import dataclass

PAGES = ("login", "products", "cart", "checkout", "confirmation")


@dataclass(frozen=True)
class Locate:
    """A locator as plain data: kind is id, css, xpath or text."""

    kind: str
    value: str


@dataclass(frozen=True)
class Element:
    """One element that tests interact with, with its baseline and mutated values."""

    name: str
    page: str
    tag: str
    generic_class: str
    el_id: str
    css_class: str
    qa: str
    text: str
    mutated_id: str
    mutated_class: str
    mutated_qa: str
    mutated_text: str
    extra: tuple[tuple[str, str], ...] = ()

    @property
    def kinds(self) -> tuple[str, ...]:
        """Locator kinds that resolve this element at baseline."""
        return ("id", "css", "xpath", "text") if self.text else ("id", "css", "xpath")

    def locator(self, kind: str) -> Locate:
        """The baseline locator of the given kind (id, css, xpath or text)."""
        if kind == "id":
            return Locate("id", self.el_id)
        if kind == "css":
            return Locate("css", f"{self.tag}.{self.css_class}")
        if kind == "xpath":
            return Locate("xpath", f"//{self.tag}[@data-qa='{self.qa}']")
        if kind == "text" and self.text:
            return Locate("text", self.text)
        raise ValueError(f"element {self.name} has no {kind} locator")


def _e(**fields: object) -> Element:
    return Element(**fields)  # type: ignore[arg-type]


ELEMENTS: dict[str, Element] = {
    e.name: e
    for e in (
        _e(
            name="username",
            page="login",
            tag="input",
            generic_class="field",
            el_id="username",
            css_class="field-username",
            qa="login-user",
            text="",
            mutated_id="user-email",
            mutated_class="input-email",
            mutated_qa="auth-user",
            mutated_text="",
            extra=(("type", "text"), ("name", "username"), ("placeholder", "Email address")),
        ),
        _e(
            name="password",
            page="login",
            tag="input",
            generic_class="field",
            el_id="password",
            css_class="field-password",
            qa="login-pass",
            text="",
            mutated_id="user-secret",
            mutated_class="input-secret",
            mutated_qa="auth-pass",
            mutated_text="",
            extra=(("type", "password"), ("name", "password"), ("placeholder", "Password")),
        ),
        _e(
            name="login_submit",
            page="login",
            tag="button",
            generic_class="btn",
            el_id="login-button",
            css_class="btn-login",
            qa="login-submit",
            text="Log in",
            mutated_id="signin-btn",
            mutated_class="btn-signin",
            mutated_qa="auth-submit",
            mutated_text="Sign in",
            extra=(("type", "submit"),),
        ),
        _e(
            name="add_backpack",
            page="products",
            tag="button",
            generic_class="btn",
            el_id="add-backpack",
            css_class="btn-add-backpack",
            qa="add-bp",
            text="Add Backpack to cart",
            mutated_id="buy-backpack",
            mutated_class="btn-buy-backpack",
            mutated_qa="buy-bp",
            mutated_text="Buy Backpack",
            extra=(("type", "submit"),),
        ),
        _e(
            name="cart_link",
            page="products",
            tag="a",
            generic_class="nav-link",
            el_id="cart-link",
            css_class="nav-cart",
            qa="cart-nav",
            text="View shopping cart",
            mutated_id="basket-link",
            mutated_class="nav-basket",
            mutated_qa="basket-nav",
            mutated_text="Basket",
            extra=(("href", "/cart"),),
        ),
        _e(
            name="remove_item",
            page="cart",
            tag="button",
            generic_class="btn",
            el_id="remove-backpack",
            css_class="btn-remove",
            qa="remove-bp",
            text="Remove Backpack",
            mutated_id="delete-backpack",
            mutated_class="btn-delete",
            mutated_qa="delete-bp",
            mutated_text="Delete item",
            extra=(("type", "submit"),),
        ),
        _e(
            name="checkout_button",
            page="cart",
            tag="button",
            generic_class="btn",
            el_id="checkout-button",
            css_class="btn-checkout",
            qa="go-checkout",
            text="Proceed to checkout",
            mutated_id="pay-button",
            mutated_class="btn-pay",
            mutated_qa="go-pay",
            mutated_text="Continue to payment",
            extra=(("type", "submit"),),
        ),
        _e(
            name="ship_name",
            page="checkout",
            tag="input",
            generic_class="field",
            el_id="ship-name",
            css_class="field-name",
            qa="ship-fullname",
            text="",
            mutated_id="recipient",
            mutated_class="input-recipient",
            mutated_qa="ship-recipient",
            mutated_text="",
            extra=(("type", "text"), ("name", "name"), ("placeholder", "Full name")),
        ),
        _e(
            name="place_order",
            page="checkout",
            tag="button",
            generic_class="btn",
            el_id="place-order",
            css_class="btn-place-order",
            qa="order-submit",
            text="Place order",
            mutated_id="confirm-order",
            mutated_class="btn-confirm",
            mutated_qa="order-confirm",
            mutated_text="Complete purchase",
            extra=(("type", "submit"),),
        ),
        _e(
            name="confirmation",
            page="confirmation",
            tag="h2",
            generic_class="message",
            el_id="confirmation",
            css_class="msg-confirmation",
            qa="order-done",
            text="Thank you for your order",
            mutated_id="order-complete",
            mutated_class="msg-complete",
            mutated_qa="done-msg",
            mutated_text="Order received",
        ),
    )
}
