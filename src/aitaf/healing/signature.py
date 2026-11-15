"""Expected-element signature derived from a stored locator (FR-23).

When the Execution Engine has no baseline snapshot of the original element, the
healer still knows something about it from the locator record: an id, the tag and
classes in a CSS selector, the text in a text strategy, and so on. Primary
strategies take precedence over fallbacks.
"""

from __future__ import annotations

from aitaf.core.healing import ElementSignature
from aitaf.core.models import Locator, LocatorStrategy
from aitaf.healing.resolver import X_ATTR, X_TEXT, XPATH, parse_css


def _from_css(value: str, tag: list[str], attrs: dict[str, str]) -> None:
    chain = parse_css(value)
    if not chain:
        return
    last = chain[-1]
    if last.tag and not tag:
        tag.append(last.tag.lower())
    if last.ids:
        attrs.setdefault("id", last.ids[0])
    if last.classes:
        attrs.setdefault("class", " ".join(last.classes))
    for name, op, expected in last.attrs:
        if op == "=" and expected is not None:
            attrs.setdefault(name, expected)


def _from_xpath(value: str, tag: list[str], attrs: dict[str, str], text: list[str]) -> None:
    parsed = XPATH.match(value.strip())
    if not parsed:
        return
    if parsed.group("tag") != "*" and not tag:
        tag.append(parsed.group("tag").lower())
    pred = (parsed.group("pred") or "").strip()
    if m := X_ATTR.match(pred):
        attrs.setdefault(m.group(1).lower(), m.group(2) if m.group(2) is not None else m.group(3))
    elif m := X_TEXT.match(pred):
        if not text:
            text.append(m.group(1) if m.group(1) is not None else m.group(2))


def signature_from_locator(locator: Locator) -> ElementSignature:
    """Partial description of the original element, built from its stored strategies."""
    tag: list[str] = []
    attrs: dict[str, str] = {}
    text: list[str] = []
    strategies: list[LocatorStrategy] = [locator.primary, *locator.fallbacks]
    for strategy in strategies:
        kind, value = strategy.kind, strategy.value
        if kind == "id":
            attrs.setdefault("id", value)
        elif kind == "css":
            _from_css(value, tag, attrs)
        elif kind == "xpath":
            _from_xpath(value, tag, attrs, text)
        elif kind == "text":
            if not text:
                text.append(value)
        elif kind == "role":
            attrs.setdefault("role", value)
        else:
            name, sep, expected = value.partition("=")
            if sep:
                attrs.setdefault(name.strip().lower(), expected.strip())
    return ElementSignature(tag=tag[0] if tag else None, attrs=attrs, text=text[0] if text else "")
