"""Baseline DOM snapshots: recover what the original element looked like (FR-23, FR-24).

Given a directory of approved snapshots (HTML files of the pages when the tests
last passed), :class:`BaselineSnapshots` finds the page on which a stored locator
resolves to exactly one element and returns that element's signature. The healer
then compares every candidate with this signature instead of with a guess made
from the locator text alone. An ambiguous locator is skipped rather than guessed: the
strategy must resolve to one element, and to the same element on every snapshot where
it resolves.
"""

from __future__ import annotations

from pathlib import Path

from aitaf.core.errors import ValidationError
from aitaf.core.healing import ElementSignature
from aitaf.core.models import Locator
from aitaf.healing.dom import Dom, parse_dom, signature_of
from aitaf.healing.resolver import find_elements


class BaselineSnapshots:
    """A set of parsed baseline pages; unreadable files are ignored."""

    def __init__(self, directory: Path | str) -> None:
        self._doms: list[Dom] = []
        root = Path(directory)
        if not root.is_dir():
            return
        for path in sorted(root.glob("*.html")):
            try:
                self._doms.append(parse_dom(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError, ValidationError):
                continue

    def __len__(self) -> int:
        return len(self._doms)

    def signature_for(self, locator: Locator) -> ElementSignature | None:
        """Signature of the element the locator meant, or None if it cannot be told."""
        for strategy in [locator.primary, *locator.fallbacks]:
            seen: list[ElementSignature] = []
            for dom in self._doms:
                found = find_elements(dom, strategy)
                if found is not None and len(found) == 1:
                    signature = signature_of(dom, found[0])
                    if signature not in seen:
                        seen.append(signature)
            if len(seen) == 1:  # the same element on every page where it resolves
                return seen[0]
        return None
