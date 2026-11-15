"""DOM-similarity scoring of candidate elements (FR-23, second rung).

A candidate is compared with the expected element on four components: tag,
attributes, visible text, and context (the path of ancestor tags and the text of
neighbouring elements). Components for which the expected signature holds no
information are left out and the weights of the rest are renormalised, so a
sparse signature is not penalised for what it cannot say.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from aitaf.core.healing import ElementSignature
from aitaf.healing.dom import Dom, DomElement, normalise

WEIGHTS = {"tag": 0.2, "attrs": 0.3, "text": 0.3, "context": 0.2}
_IGNORED_ATTRS = frozenset({"style"})
_NOT_CANDIDATES = frozenset({"html", "head", "body", "title", "meta", "link", "style", "script"})


def candidate_text(element: DomElement) -> str:
    return element.own_text or element.text


def text_ratio(a: str, b: str) -> float:
    left, right = normalise(a).lower(), normalise(b).lower()
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _pairs(attrs: dict[str, str]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for name, value in attrs.items():
        if name in _IGNORED_ATTRS:
            continue
        if name == "class":
            pairs.update((name, token) for token in value.split())
        else:
            pairs.add((name, value.strip()))
    return pairs


def _attr_score(expected: set[tuple[str, str]], found: set[tuple[str, str]]) -> float:
    shared = len(expected & found)
    recall = shared / len(expected)
    jaccard = shared / len(expected | found)
    return (recall + jaccard) / 2


def context_score(expected: ElementSignature, dom: Dom, candidate: DomElement) -> float | None:
    """Mean of ancestor-path and neighbour-text similarity; None if nothing to compare."""
    scores: list[float] = []
    if expected.ancestors:
        found = [dom.elements[i].tag for i in dom.ancestors(candidate)]
        scores.append(SequenceMatcher(None, list(expected.ancestors), found).ratio())
    if expected.neighbours:
        siblings = dom.siblings(candidate)
        at = siblings.index(candidate.index)
        near = [siblings[i] for i in (at - 1, at + 1) if 0 <= i < len(siblings)]
        found_texts = {t for t in (normalise(dom.elements[i].text).lower() for i in near) if t}
        wanted = set(expected.neighbours)
        union = wanted | found_texts
        scores.append(len(wanted & found_texts) / len(union) if union else 0.0)
    return sum(scores) / len(scores) if scores else None


def similarity(expected: ElementSignature, dom: Dom, candidate: DomElement) -> float:
    """Score in [0, 1] of how well ``candidate`` matches the expected element."""
    parts: list[tuple[float, float]] = []
    if expected.tag:
        parts.append((WEIGHTS["tag"], 1.0 if expected.tag == candidate.tag else 0.0))
    wanted = _pairs(expected.attrs)
    if wanted:
        parts.append((WEIGHTS["attrs"], _attr_score(wanted, _pairs(candidate.attrs))))
    if expected.text:
        parts.append((WEIGHTS["text"], text_ratio(expected.text, candidate_text(candidate))))
    context = context_score(expected, dom, candidate)
    if context is not None:
        parts.append((WEIGHTS["context"], context))
    total = sum(weight for weight, _ in parts)
    if total == 0:
        return 0.0
    return min(1.0, max(0.0, sum(weight * score for weight, score in parts) / total))


def rank(expected: ElementSignature, dom: Dom) -> list[tuple[float, DomElement]]:
    """All plausible candidates, best first (ties keep document order)."""
    scored = [
        (similarity(expected, dom, e), e) for e in dom.elements if e.tag not in _NOT_CANDIDATES
    ]
    return sorted(scored, key=lambda item: (-item[0], item[1].index))
