"""Self-Healing Engine (FR-22 to FR-26)."""

from aitaf.healing.approval import approve_healing_event, update_locator_from_event
from aitaf.healing.baseline import BaselineSnapshots
from aitaf.healing.classify import classify_failure
from aitaf.healing.dom import Dom, DomElement, parse_dom, role_of, signature_of
from aitaf.healing.engine import HealingConfig, SelfHealingEngine
from aitaf.healing.llm_step import COMPONENT
from aitaf.healing.metrics import success_rates
from aitaf.healing.mock_responder import mock_healing_responder
from aitaf.healing.resolver import find_elements
from aitaf.healing.signature import signature_from_locator
from aitaf.healing.similarity import WEIGHTS, rank, similarity
from aitaf.healing.validate import Validation, validate_candidate

__all__ = [
    "COMPONENT",
    "WEIGHTS",
    "BaselineSnapshots",
    "Dom",
    "DomElement",
    "HealingConfig",
    "SelfHealingEngine",
    "Validation",
    "approve_healing_event",
    "classify_failure",
    "find_elements",
    "mock_healing_responder",
    "parse_dom",
    "rank",
    "role_of",
    "signature_from_locator",
    "signature_of",
    "similarity",
    "success_rates",
    "update_locator_from_event",
    "validate_candidate",
]
