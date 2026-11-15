"""Locator strategies evaluated against a DOM snapshot (FR-16, FR-23).

Supports the subset of CSS and XPath that generated locators use. A selector
outside that subset yields ``None`` ("cannot say") rather than a wrong answer;
the healer then simply skips it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from aitaf.core.models import LocatorStrategy
from aitaf.healing.dom import Dom, DomElement, role_of

_QUOTES = "\"'"
_TAG = re.compile(r"^(\*|[A-Za-z][\w-]*)?")
_ID = re.compile(r"#([\w-]+)")
_CLASS = re.compile(r"\.([\w-]+)")
_ATTR = re.compile(r"""\[\s*([\w:-]+)\s*(?:(\^=|\$=|\*=|=)\s*("[^"]*"|'[^']*'|[^\]\s]+))?\s*\]""")
XPATH = re.compile(r"^//(?P<tag>\*|[A-Za-z][\w-]*)(?:\[(?P<pred>.+)\])?$")
_STR = r"""(?:'([^']*)'|"([^"]*)")"""
X_ATTR = re.compile(rf"^@([\w:-]+)\s*=\s*{_STR}$")
X_TEXT = re.compile(rf"^text\(\)\s*=\s*{_STR}$")
_X_CONTAINS_ATTR = re.compile(rf"^contains\(\s*@([\w:-]+)\s*,\s*{_STR}\s*\)$")
_X_CONTAINS_TEXT = re.compile(rf"^contains\(\s*text\(\)\s*,\s*{_STR}\s*\)$")


@dataclass
class Compound:
    """One CSS compound selector such as ``button.btn[type=submit]``."""

    tag: str | None = None
    ids: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    attrs: list[tuple[str, str | None, str | None]] = field(default_factory=list)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in _QUOTES:
        return value[1:-1]
    return value


def _split_selector(selector: str) -> list[str] | None:
    """Split on whitespace outside brackets and quotes."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    quote = ""
    for ch in selector.strip():
        if quote:
            if ch == quote:
                quote = ""
        elif ch in _QUOTES:
            quote = ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch.isspace() and depth == 0 and not quote:
            if current:
                parts.append("".join(current))
                current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts if parts and depth == 0 and not quote else None


def _parse_compound(token: str) -> Compound | None:
    match = _TAG.match(token)
    head = match.group(1) if match else None
    compound = Compound(tag=None if head in (None, "*") else head)
    rest = token[match.end() if match else 0 :]
    if head is None and not rest:
        return None
    while rest:
        if rest[0] == "#" and (m := _ID.match(rest)):
            compound.ids.append(m.group(1))
        elif rest[0] == "." and (m := _CLASS.match(rest)):
            compound.classes.append(m.group(1))
        elif rest[0] == "[" and (m := _ATTR.match(rest)):
            value = _unquote(m.group(3)) if m.group(3) is not None else None
            compound.attrs.append((m.group(1).lower(), m.group(2), value))
        else:
            return None
        rest = rest[m.end() :]
    return compound


def parse_css(selector: str) -> list[Compound] | None:
    """Parse a descendant chain of compound selectors, or None if unsupported."""
    tokens = _split_selector(selector)
    if tokens is None:
        return None
    chain: list[Compound] = []
    for token in tokens:
        compound = _parse_compound(token)
        if compound is None:
            return None
        chain.append(compound)
    return chain


def _attr_ok(element: DomElement, name: str, op: str | None, value: str | None) -> bool:
    if name not in element.attrs:
        return False
    actual = element.attrs[name]
    if op is None or value is None:
        return True
    return {
        "=": actual == value,
        "^=": actual.startswith(value),
        "$=": actual.endswith(value),
        "*=": value in actual,
    }[op]


def _compound_matches(element: DomElement, compound: Compound) -> bool:
    if compound.tag and element.tag != compound.tag.lower():
        return False
    if any(element.attrs.get("id") != i for i in compound.ids):
        return False
    tokens = set(element.attrs.get("class", "").split())
    if not set(compound.classes) <= tokens:
        return False
    return all(_attr_ok(element, n, o, v) for n, o, v in compound.attrs)


def _css(dom: Dom, selector: str) -> list[DomElement] | None:
    chain = parse_css(selector)
    if chain is None:
        return None
    found: list[DomElement] = []
    for element in dom.elements:
        if not _compound_matches(element, chain[-1]):
            continue
        wanted = len(chain) - 2
        for ancestor in reversed(dom.ancestors(element)):
            if wanted < 0:
                break
            if _compound_matches(dom.elements[ancestor], chain[wanted]):
                wanted -= 1
        if wanted < 0:
            found.append(element)
    return found


def _quoted(match: re.Match[str], first: int) -> str:
    value = match.group(first)
    return value if value is not None else match.group(first + 1)


def _xpath(dom: Dom, expression: str) -> list[DomElement] | None:
    parsed = XPATH.match(expression.strip())
    if not parsed:
        return None
    tag = parsed.group("tag")
    pred = parsed.group("pred")
    candidates = [e for e in dom.elements if tag == "*" or e.tag == tag.lower()]
    if pred is None:
        return candidates
    pred = pred.strip()
    if pred.isdigit():
        return [e for e in candidates if e.position == int(pred)]
    if m := X_ATTR.match(pred):
        name, value = m.group(1).lower(), _quoted(m, 2)
        return [e for e in candidates if e.attrs.get(name) == value]
    if m := X_TEXT.match(pred):
        value = _quoted(m, 1)
        return [e for e in candidates if e.own_text == value]
    if m := _X_CONTAINS_ATTR.match(pred):
        name, value = m.group(1).lower(), _quoted(m, 2)
        return [e for e in candidates if value in e.attrs.get(name, "")]
    if m := _X_CONTAINS_TEXT.match(pred):
        value = _quoted(m, 1)
        return [e for e in candidates if value in e.own_text]
    return None


def find_elements(dom: Dom, strategy: LocatorStrategy) -> list[DomElement] | None:
    """Elements matching the strategy in document order; None if it cannot be evaluated."""
    kind, value = strategy.kind, strategy.value
    if kind == "id":
        return [e for e in dom.elements if e.attrs.get("id") == value]
    if kind == "css":
        return _css(dom, value)
    if kind == "xpath":
        return _xpath(dom, value)
    if kind == "text":
        needle = value.lower()
        return [e for e in dom.elements if e.own_text and needle in e.own_text.lower()]
    if kind == "role":
        return [e for e in dom.elements if role_of(e.tag, e.attrs) == value.lower()]
    name, sep, expected = value.partition("=")
    name = name.strip().lower()
    if not sep:
        return [e for e in dom.elements if name in e.attrs]
    wanted = _unquote(expected.strip())
    return [e for e in dom.elements if e.attrs.get(name) == wanted]
