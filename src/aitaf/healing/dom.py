"""DOM snapshot model and parser (FR-22 to FR-24, NFR-10).

The Execution Engine hands the healer an HTML snapshot taken at the moment of
failure. It is untrusted input: it is size-limited, parsed with the standard
library (no scripts run), and the content of script, style and title elements is
dropped. The healer works only on this parsed snapshot, so it needs no browser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

from aitaf.core.errors import ValidationError
from aitaf.core.healing import ElementSignature

MAX_DOM_CHARS = 500_000
MAX_ELEMENTS = 5000

_VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_IGNORED_TEXT = frozenset({"script", "style", "title"})
_BUTTON_INPUTS = frozenset({"button", "submit", "reset", "image"})
_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_TEXT_CAP = 200


def normalise(text: str) -> str:
    return " ".join(text.split())


@dataclass
class DomElement:
    """One element of the snapshot, with its place in the tree."""

    index: int
    tag: str
    attrs: dict[str, str]
    parent: int | None
    depth: int
    position: int
    own_text: str = ""
    text: str = ""
    children: list[int] = field(default_factory=list)


@dataclass
class Dom:
    """Parsed snapshot: elements in document order."""

    elements: list[DomElement]

    def ancestors(self, element: DomElement) -> list[int]:
        """Indices of the element's ancestors, root first."""
        chain: list[int] = []
        parent = element.parent
        while parent is not None:
            chain.append(parent)
            parent = self.elements[parent].parent
        chain.reverse()
        return chain

    def siblings(self, element: DomElement) -> list[int]:
        if element.parent is None:
            return [e.index for e in self.elements if e.parent is None]
        return self.elements[element.parent].children


def role_of(tag: str | None, attrs: dict[str, str]) -> str | None:
    """Explicit ARIA role, else the implicit role of the tag."""
    explicit = attrs.get("role", "").strip().lower()
    if explicit:
        return explicit
    if tag is None:
        return None
    if tag == "button":
        return "button"
    if tag == "a":
        return "link" if "href" in attrs else None
    if tag == "input":
        kind = attrs.get("type", "text").lower()
        if kind in _BUTTON_INPUTS:
            return "button"
        if kind in ("checkbox", "radio"):
            return kind
        return None if kind == "hidden" else "textbox"
    if tag == "textarea":
        return "textbox"
    if tag == "select":
        return "combobox"
    if tag in _HEADINGS:
        return "heading"
    return {"img": "img", "nav": "navigation", "ul": "list", "ol": "list", "li": "listitem"}.get(
        tag
    )


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[DomElement] = []
        self._stack: list[int] = []
        self._pieces: dict[int, list[str]] = {}

    def _open(self, tag: str, attrs: list[tuple[str, str | None]]) -> int:
        if len(self.elements) >= MAX_ELEMENTS:
            raise ValidationError(f"DOM snapshot has too many elements (limit {MAX_ELEMENTS})")
        parent = self._stack[-1] if self._stack else None
        siblings = (
            self.elements[parent].children
            if parent is not None
            else [e.index for e in self.elements if e.parent is None]
        )
        position = 1 + sum(1 for i in siblings if self.elements[i].tag == tag)
        element = DomElement(
            index=len(self.elements),
            tag=tag,
            attrs={name.lower(): value or "" for name, value in attrs},
            parent=parent,
            depth=len(self._stack),
            position=position,
        )
        self.elements.append(element)
        if parent is not None:
            self.elements[parent].children.append(element.index)
        self._pieces[element.index] = []
        return element.index

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        index = self._open(tag, attrs)
        if tag not in _VOID:
            self._stack.append(index)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        for depth in range(len(self._stack) - 1, -1, -1):
            if self.elements[self._stack[depth]].tag == tag:
                del self._stack[depth:]
                return

    def handle_data(self, data: str) -> None:
        if not self._stack:
            return
        current = self._stack[-1]
        if self.elements[current].tag in _IGNORED_TEXT:
            return
        self._pieces[current].append(data)

    def finish(self) -> list[DomElement]:
        """Fill in own and full text once every element is known."""
        elements = self.elements
        for element in elements:
            element.own_text = normalise(" ".join(self._pieces[element.index]))[:_TEXT_CAP]
        for element in reversed(elements):
            parts = [element.own_text, *(elements[c].text for c in element.children)]
            element.text = normalise(" ".join(p for p in parts if p))[:_TEXT_CAP]
        return elements


def parse_dom(html: str) -> Dom:
    """Parse an HTML snapshot; raise :class:`ValidationError` if it is unusable."""
    if not isinstance(html, str):
        raise ValidationError(f"DOM snapshot must be text, got {type(html).__name__}")
    if len(html) > MAX_DOM_CHARS:
        raise ValidationError(f"DOM snapshot is too large (limit {MAX_DOM_CHARS} characters)")
    builder = _Builder()
    builder.feed(html)
    builder.close()
    return Dom(elements=builder.finish())


def signature_of(dom: Dom, element: DomElement) -> ElementSignature:
    """What the element looks like and where it sits, for later comparison."""
    siblings = dom.siblings(element)
    at = siblings.index(element.index)
    near = [siblings[i] for i in (at - 1, at + 1) if 0 <= i < len(siblings)]
    neighbours = tuple(t for t in (normalise(dom.elements[i].text).lower() for i in near) if t)
    return ElementSignature(
        tag=element.tag,
        attrs=dict(element.attrs),
        text=element.own_text or element.text,
        ancestors=tuple(dom.elements[i].tag for i in dom.ancestors(element)),
        neighbours=neighbours,
    )
