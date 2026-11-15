"""Deterministic stand-in for the LLM test-design step (FR-36).

Reads the requirement record between the prompt delimiters and returns one
positive, one negative and one boundary case in the schema a real model must
produce, so the generator runs offline on fixtures and in CI.
"""

from __future__ import annotations

import json
import re
from typing import Any

from aitaf.core.llm import LlmRequest
from aitaf.generator.prompts import CLOSE, OPEN

_LINE = re.compile(r"^(Requirement ID|Actors|Actions|Preconditions|Outcomes|Risk): ?(.*)$")
_PRIORITY = {"High": "M", "Medium": "S", "Low": "C"}
_MODAL_PREFIX = re.compile(
    r"^(?:the system|an? \w+)\s+(?:shall|must|should|can|will)\s+(?:be able to\s+)?", re.IGNORECASE
)


def _record(prompt: str) -> dict[str, str]:
    start = prompt.rindex(OPEN) + len(OPEN)
    end = prompt.index(CLOSE, start)
    fields: dict[str, str] = {}
    for line in prompt[start:end].strip().split("\n"):
        match = _LINE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def _first(value: str, default: str) -> str:
    return next((part.strip() for part in value.split(";") if part.strip()), default)


def mock_generation_responder(req: LlmRequest) -> str:
    fields = _record(req.prompt)
    actor = _first(fields.get("Actors", ""), "user")
    action = _MODAL_PREFIX.sub("", _first(fields.get("Actions", ""), "use the feature"))
    outcome = _first(fields.get("Outcomes", ""), "the system behaves as specified")
    priority = _PRIORITY.get(fields.get("Risk", "Low"), "C")
    setup = f"Open the application as a {actor}"
    preconditions = [f"Role under test: {actor}"]

    def case(
        title: str, step: str, observe: str, expected: str, data: dict[str, str]
    ) -> dict[str, Any]:
        return {
            "title": title,
            "preconditions": preconditions,
            "steps": [setup, step, observe],
            "expected": [expected],
            "priority": priority,
            "data": data,
        }

    scenarios = [
        {
            "kind": "positive",
            "description": f"A {actor} succeeds with valid input",
            "cases": [
                case(
                    f"Verify that a {actor} can {action}",
                    f"Perform the action with valid input: {action}",
                    "Observe the result",
                    outcome,
                    {"email": "demo.user@example.test", "name": "Test User"},
                )
            ],
        },
        {
            "kind": "negative",
            "description": f"A {actor} is stopped when input is invalid or missing",
            "cases": [
                case(
                    f"Reject invalid input when a {actor} tries to {action}",
                    f"Attempt the action with invalid or missing input: {action}",
                    "Observe the error handling",
                    "The system rejects the input with a clear error message and changes no data",
                    {"email": "not-an-email"},
                )
            ],
        },
        {
            "kind": "boundary",
            "description": f"A {actor} uses values at the stated limits",
            "cases": [
                case(
                    f"Check boundary values when a {actor} tries to {action}",
                    f"Repeat the action with values at and just beyond each limit: {action}",
                    "Observe the result at each limit",
                    "Values at the limit are accepted and values beyond it are rejected",
                    {},
                )
            ],
        },
    ]
    return json.dumps({"scenarios": scenarios})
