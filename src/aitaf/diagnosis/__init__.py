"""Failure Analyzer: classify failed tests, explain them and group similar ones.

Requirements: FR-27 (category), FR-28 (cause, evidence, next step), FR-29 (clusters,
confidence), FR-30 (redaction before any model call), NFR-10, NFR-13, NFR-30.
"""

from aitaf.diagnosis.analyzer import AnalysisResult, FailureAnalyzer
from aitaf.diagnosis.mock_responder import mock_failure_responder
from aitaf.diagnosis.prompt import COMPONENT, PROMPT_VERSION
from aitaf.diagnosis.rules import FailureFacts, Verdict, classify
from aitaf.diagnosis.signature import cluster_id, normalise_text

__all__ = [
    "COMPONENT",
    "PROMPT_VERSION",
    "AnalysisResult",
    "FailureAnalyzer",
    "FailureFacts",
    "Verdict",
    "classify",
    "cluster_id",
    "mock_failure_responder",
    "normalise_text",
]
