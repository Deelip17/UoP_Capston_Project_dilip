"""Deterministic stand-in for the model's failure explanation (FR-36).

Reads the exception type and text from the prompt block and answers with a cautious
category: a timeout is called timing, everything else stays unknown with low
confidence, which is what an honest offline answer should say.
"""

from __future__ import annotations

import json
import re

from aitaf.core.llm import LlmRequest
from aitaf.diagnosis.prompt import CLOSE, OPEN


def mock_failure_responder(req: LlmRequest) -> str:
    start = req.prompt.rindex(OPEN) + len(OPEN)
    block = req.prompt[start : req.prompt.index(CLOSE, start)]
    kind = next(iter(re.findall(r"^Exception type: (.*)$", block, re.MULTILINE)), "")
    text = next(iter(re.findall(r"^Exception text: (.*)$", block, re.MULTILINE)), "")
    if "timeout" in f"{kind} {text}".lower():
        answer = {
            "category": "timing_flaky",
            "root_cause": "The failure looks like a timeout.",
            "remediation": "Rerun and wait for an explicit condition.",
            "confidence": 0.5,
        }
    else:
        answer = {
            "category": "unknown",
            "root_cause": f"The failure ({kind or 'no exception type'}) matches no known pattern.",
            "remediation": "Inspect the screenshot and the log, then classify it by hand.",
            "confidence": 0.4,
        }
    return json.dumps(answer)
