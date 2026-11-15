"""Sample shop: the local system under test with mutable locators (FR-38, NFR-08).

``python -m aitaf.sampleapp serve`` starts it; ``python -m aitaf.sampleapp
snapshot`` writes its DOM snapshots. It imports nothing from the framework.
"""

from aitaf.sampleapp.elements import ELEMENTS, PAGES, Element, Locate
from aitaf.sampleapp.mutations import CATALOGUE, Mutation, get_mutation
from aitaf.sampleapp.pages import render_page
from aitaf.sampleapp.server import ShopServer
from aitaf.sampleapp.snapshots import write_snapshots

__all__ = [
    "CATALOGUE",
    "ELEMENTS",
    "PAGES",
    "Element",
    "Locate",
    "Mutation",
    "ShopServer",
    "get_mutation",
    "render_page",
    "write_snapshots",
]
