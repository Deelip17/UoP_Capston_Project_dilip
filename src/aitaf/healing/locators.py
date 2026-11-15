"""Deriving a unique replacement locator for a chosen element (FR-14, FR-23).

A healed locator is only proposed if it identifies exactly the chosen element in
the snapshot. Stable attributes come first; positional locators are deliberately
not used because they break again at the next layout change.
"""

from __future__ import annotations

from aitaf.core.models import LocatorStrategy
from aitaf.healing.dom import Dom, DomElement
from aitaf.healing.resolver import find_elements

_STABLE_ATTRS = ("data-testid", "data-test", "data-qa", "name", "aria-label")


def resolves_uniquely(dom: Dom, strategy: LocatorStrategy, element: DomElement) -> bool:
    found = find_elements(dom, strategy)
    return found is not None and len(found) == 1 and found[0].index == element.index


def unique_strategy_for(dom: Dom, element: DomElement) -> LocatorStrategy | None:
    """First strategy, in order of stability, that finds only this element."""
    attrs = element.attrs
    options: list[LocatorStrategy] = []
    if attrs.get("id"):
        options.append(LocatorStrategy(kind="id", value=attrs["id"]))
    options.extend(
        LocatorStrategy(kind="attr", value=f"{name}={attrs[name]}")
        for name in _STABLE_ATTRS
        if attrs.get(name)
    )
    classes = attrs.get("class", "").split()
    if classes:
        options.append(
            LocatorStrategy(kind="css", value=element.tag + "".join(f".{c}" for c in classes))
        )
    if attrs.get("type"):
        options.append(LocatorStrategy(kind="css", value=f"{element.tag}[type={attrs['type']}]"))
    if element.own_text:
        options.append(LocatorStrategy(kind="text", value=element.own_text))
    return next((o for o in options if resolves_uniquely(dom, o, element)), None)
