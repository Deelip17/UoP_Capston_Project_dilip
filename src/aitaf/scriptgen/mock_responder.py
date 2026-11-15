"""Deterministic stand-in for the LLM automation-planning step (FR-36).

Returns a schema-valid plan (page, three locators with two fallbacks each, and a
short step list) for any test case, using the first synthetic data value if one
is supplied, so the Script Generator runs offline and in CI.
"""

from __future__ import annotations

import json
import re

from aitaf.core.llm import LlmRequest
from aitaf.scriptgen.prompts import CLOSE, OPEN

_DATA = re.compile(r"^Data: ?(.*)$", re.MULTILINE)


def _first_data_value(prompt: str) -> str:
    start = prompt.rindex(OPEN) + len(OPEN)
    end = prompt.index(CLOSE, start)
    match = _DATA.search(prompt[start:end])
    if match:
        first = match.group(1).split("; ")[0]
        value = first.partition("=")[2].strip()
        if value:
            return value
    return "synthetic-value"


def mock_script_responder(req: LlmRequest) -> str:
    value = _first_data_value(req.prompt)
    plan = {
        "page": "app",
        "locators": [
            {
                "name": "main_input",
                "primary": {"kind": "id", "value": "main-input"},
                "fallbacks": [
                    {"kind": "css", "value": '[data-testid="main-input"]'},
                    {"kind": "xpath", "value": "//input[1]"},
                ],
            },
            {
                "name": "submit_button",
                "primary": {"kind": "id", "value": "submit"},
                "fallbacks": [
                    {"kind": "css", "value": "button[type=submit]"},
                    {"kind": "text", "value": "Submit"},
                ],
            },
            {
                "name": "result_message",
                "primary": {"kind": "id", "value": "result"},
                "fallbacks": [
                    {"kind": "css", "value": ".result"},
                    {"kind": "attr", "value": "data-testid=result"},
                ],
            },
        ],
        "steps": [
            {"action": "open", "value": "/"},
            {"action": "type", "target": "main_input", "value": value},
            {"action": "click", "target": "submit_button"},
            {"action": "assert_visible", "target": "result_message"},
        ],
    }
    return json.dumps(plan)
