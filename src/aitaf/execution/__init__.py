"""Execution Engine: run generated scripts under an allow-list and store the results.

Requirements: FR-17 (PyTest on Playwright or Selenium), FR-18 (screenshots), FR-19
(results stored), FR-20 (headless, timeouts, retries, workers), FR-21 (allow-listed
base URLs), NFR-11 (least privilege).
"""

from aitaf.execution.allowlist import check_base_url
from aitaf.execution.config import RunConfig
from aitaf.execution.runner import ExecutedTest, ExecutionEngine, RunSummary, apply_strategy

__all__ = [
    "ExecutedTest",
    "ExecutionEngine",
    "RunConfig",
    "RunSummary",
    "apply_strategy",
    "check_base_url",
]
