"""The committed catalogue of locator mutations (FR-38, NFR-08).

One mutation changes one element in one way:

* ``id``: the id attribute is renamed;
* ``class``: the element's own class is renamed;
* ``xpath``: a structure change, the test-hook attribute used by the XPath is
  renamed and the element is wrapped in a new container (a typical refactor);
* ``text``: the visible text is reworded.

The catalogue is a fixed, ordered tuple, so the same seed always selects the same
mutations (the evaluation harness samples from it with a seed).
"""

from __future__ import annotations

from dataclasses import dataclass

from aitaf.sampleapp.elements import ELEMENTS

KINDS = ("id", "class", "xpath", "text")
_DESCRIPTION = {
    "id": "id attribute renamed",
    "class": "element class renamed",
    "xpath": "test-hook attribute renamed and element wrapped in a new container",
    "text": "visible text reworded",
}


@dataclass(frozen=True)
class Mutation:
    """One reproducible change to one element."""

    mutation_id: str
    element: str
    kind: str
    description: str


def _build() -> tuple[Mutation, ...]:
    out: list[Mutation] = []
    for element in ELEMENTS.values():
        for kind in KINDS:
            if kind == "text" and not element.text:
                continue
            out.append(
                Mutation(
                    mutation_id=f"M-{element.name}-{kind}",
                    element=element.name,
                    kind=kind,
                    description=f"{element.name}: {_DESCRIPTION[kind]}",
                )
            )
    return tuple(out)


CATALOGUE: tuple[Mutation, ...] = _build()
_BY_ID = {m.mutation_id: m for m in CATALOGUE}


def get_mutation(mutation_id: str) -> Mutation:
    """Return the mutation with this ID; raise :class:`KeyError` if it is unknown."""
    try:
        return _BY_ID[mutation_id]
    except KeyError:
        raise KeyError(f"unknown mutation {mutation_id!r}") from None
