"""Page catalogue: what the Script Generator may know about the application (FR-12, FR-14, FR-16).

Without it the model has only the test case, so it can only guess selectors and the
scripts do not fit the application (script executability, objective O2). The
catalogue is built from baseline HTML snapshots (the approved pages, the same files
the Self-Healing Engine uses as baseline). Per page it lists the elements a test can
use, each with the attributes a locator may be built from. The model is told to use
only these elements; :meth:`PageCatalogue.check_plan` verifies that it did, so a
guessed selector is rejected instead of saved.

Snapshots are untrusted input: they are parsed with the standard-library parser used
by the healer (no script runs), size-limited, and the rendered block is masked and
screened for prompt injection by the generator before it reaches the model.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from aitaf.core.errors import ValidationError
from aitaf.scriptgen.plan import PlanSchema

BLOCK_OPEN = "<<<PAGE_CATALOGUE"
BLOCK_CLOSE = "PAGE_CATALOGUE>>>"
MAX_ELEMENTS_PER_PAGE = 40
FLOW_FILE = "flow.txt"
MAX_HTML_CHARS = 500_000
MAX_PARSED = 5000
_VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta"})
_SKIP_TEXT = frozenset({"script", "style", "title"})
_TEXT_CAP = 60
_HOME_PAGES = frozenset({"index", "home", "login"})
_INTERACTIVE = frozenset({"input", "button", "a", "select", "textarea"})
_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_NON_NAME = re.compile(r"[^a-z0-9]+")


def _slug(text: str, fallback: str) -> str:
    slug = _NON_NAME.sub("_", text.lower()).strip("_")
    if not slug or not slug[0].isalpha():
        slug = f"{fallback}_{slug}".strip("_")
    return slug[:39]


@dataclass(frozen=True)
class CatalogueElement:
    """One element a test can use, with the facts a locator may be built from."""

    name: str
    page: str
    tag: str
    kind: str  # input, button, link, select, text
    el_id: str
    css_class: str
    qa: str
    text: str
    input_type: str = ""

    def strategies(self) -> list[tuple[str, str]]:
        """Locator strategies (kind, value) that resolve this element, most stable first."""
        found: list[tuple[str, str]] = []
        if self.el_id:
            found.append(("id", self.el_id))
        if self.css_class:
            found.append(("css", f"{self.tag}.{self.css_class}"))
        if self.qa:
            found.append(("xpath", f"//{self.tag}[@data-qa='{self.qa}']"))
        if self.text and self.kind != "input":
            found.append(("text", self.text))
        return found


class PageCatalogue:
    """Elements per page, in page-name order, with the path each page is served at."""

    def __init__(self, app: str, pages: dict[str, list[CatalogueElement]]) -> None:
        self.app = _slug(app, "app") or "app"
        self.pages = pages
        self._strategies = {
            strategy for element in self.elements() for strategy in element.strategies()
        }

    @classmethod
    def from_snapshots(cls, directory: Path | str, app: str | None = None) -> PageCatalogue:
        root = Path(directory)
        if not root.is_dir():
            raise ValidationError(f"snapshot directory not found: {root.name!r}")
        pages: dict[str, list[CatalogueElement]] = {}
        used: set[str] = set()
        for path in sorted(root.glob("*.html")):
            try:
                parsed = _parse(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, ValidationError):
                continue
            page = _slug(path.stem, "page")
            elements = list(_elements(parsed, page, used))
            if elements:
                pages[page] = elements[:MAX_ELEMENTS_PER_PAGE]
        if not pages:
            raise ValidationError(f"no usable HTML snapshots in {root.name!r}")
        return cls(app or root.name, _in_flow_order(pages, root / FLOW_FILE))

    def elements(self) -> Iterator[CatalogueElement]:
        for items in self.pages.values():
            yield from items

    @staticmethod
    def path_of(page: str) -> str:
        return "/" if page in _HOME_PAGES else f"/{page}"

    def paths(self) -> list[str]:
        return [self.path_of(page) for page in self.pages]

    def render_block(self) -> str:
        """The text shown to the model: one PAGE line, then one ELEMENT line per element."""
        lines = [f"APP {self.app}"]
        for page, items in self.pages.items():
            lines.append(f"PAGE {page} path={self.path_of(page)}")
            for e in items:
                parts = [f"ELEMENT {e.name} tag={e.tag} kind={e.kind}"]
                if e.input_type:
                    parts.append(f"type={e.input_type}")
                for key, value in (
                    ("id", e.el_id),
                    ("class", e.css_class),
                    ("data-qa", e.qa),
                ):
                    if value:
                        parts.append(f"{key}={value}")
                if e.text:
                    parts.append(f'text="{e.text}"')
                lines.append(" ".join(parts))
        return "\n".join(lines)

    def check_plan(self, plan: PlanSchema) -> list[str]:
        """Reasons the plan is not grounded in the catalogue (empty when it is)."""
        problems: list[str] = []
        if plan.page != self.app:
            problems.append(f"page must be {self.app!r}, not {plan.page!r}")
        for locator in plan.locators:
            primary = (locator.primary.kind, locator.primary.value)
            if primary not in self._strategies:
                problems.append(
                    f"locator {locator.name!r} uses {primary[0]}={primary[1]!r}, "
                    "which is not an attribute of any listed element"
                )
        known = set(self.paths())
        for step in plan.steps:
            if step.action == "open" and step.value not in known:
                problems.append(f"open {step.value!r} is not a listed page path")
        return problems


def _in_flow_order(
    pages: dict[str, list[CatalogueElement]], flow: Path
) -> dict[str, list[CatalogueElement]]:
    """Pages in the order a user meets them, from the optional ``flow.txt`` (one name per line)."""
    try:
        wanted = [_slug(line, "page") for line in flow.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError):
        return pages
    ordered = [name for name in dict.fromkeys(wanted) if name in pages]
    return {name: pages[name] for name in [*ordered, *(n for n in pages if n not in ordered)]}


@dataclass
class _Parsed:
    tag: str
    attrs: dict[str, str]
    text: str = ""
    open: bool = True
    parts: list[str] = field(default_factory=list)


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[_Parsed] = []
        self._stack: list[_Parsed] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if len(self.items) >= MAX_PARSED:
            raise ValidationError("snapshot has too many elements")
        item = _Parsed(tag, {k: v or "" for k, v in attrs})
        self.items.append(item)
        if tag in _SKIP_TEXT:
            self._skip += 1
        if tag not in _VOID:
            self._stack.append(item)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index].tag == tag:
                for done in self._stack[index:]:
                    done.text = " ".join(" ".join(done.parts).split())
                    done.open = False
                del self._stack[index:]
                break
        if tag in _SKIP_TEXT and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            for item in self._stack:
                item.parts.append(data)


def _parse(html: str) -> list[_Parsed]:
    if len(html) > MAX_HTML_CHARS:
        raise ValidationError("snapshot is too large")
    collector = _Collector()
    collector.feed(html)
    collector.close()
    for item in collector.items:
        if item.open:
            item.text = " ".join(" ".join(item.parts).split())
    return collector.items


def _kind(element: _Parsed) -> str:
    if element.tag == "a":
        return "link"
    if element.tag in _HEADINGS or element.tag not in _INTERACTIVE:
        return "text"
    return "input" if element.tag in ("input", "textarea") else element.tag


def _elements(elements: list[_Parsed], page: str, used: set[str]) -> Iterator[CatalogueElement]:
    for el in elements:
        has_hook = bool(el.attrs.get("id") or el.attrs.get("data-qa"))
        usable = (el.tag in _INTERACTIVE and el.attrs.get("type") != "hidden" and has_hook) or (
            el.tag in _HEADINGS and bool(el.attrs.get("id"))
        )
        if not usable:
            continue
        ident = el.attrs.get("id", "")
        qa = el.attrs.get("data-qa", "")
        name = _slug(ident or qa, el.tag)
        base, n = name, 1
        while name in used:
            n += 1
            name = f"{base[:36]}_{n}"
        used.add(name)
        classes = el.attrs.get("class", "").split()
        yield CatalogueElement(
            name=name,
            page=page,
            tag=el.tag,
            kind=_kind(el),
            el_id=ident,
            css_class=classes[-1] if classes else "",
            qa=qa,
            text=" ".join(el.text.split())[:_TEXT_CAP],
            input_type=el.attrs.get("type", "") if el.tag == "input" else "",
        )
