"""Deterministic stand-in for the LLM locator suggestion (FR-36).

Reads the intent and candidate list between the prompt delimiters and picks the
candidate with the expected tag whose text shares most words with the expected
text, then answers with an id or class locator for it.
"""

from __future__ import annotations

import json
import re

from aitaf.core.llm import LlmRequest
from aitaf.healing.llm_step import CLOSE, OPEN

_LINE = re.compile(r"^\[(\d+)\] <(\w+)>(.*)$")
_ATTR = re.compile(r'([\w-]+)="([^"]*)"')


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def mock_healing_responder(req: LlmRequest) -> str:
    start = req.prompt.rindex(OPEN) + len(OPEN)
    block = req.prompt[start : req.prompt.index(CLOSE, start)]
    tag = next((m.group(1) for m in re.finditer(r"^Expected tag: (\w+)$", block, re.M)), None)
    text = next((m.group(1) for m in re.finditer(r"^Expected text: (.*)$", block, re.M)), "")
    best: tuple[int, str, dict[str, str]] | None = None
    for raw in block.splitlines():
        match = _LINE.match(raw)
        if not match or (tag and match.group(2) != tag):
            continue
        attrs = dict(_ATTR.findall(match.group(3)))
        overlap = len(_words(text) & _words(attrs.get("text", "")))
        if best is None or overlap > best[0]:
            best = (overlap, match.group(2), attrs)
    if best is None:
        strategy = {"kind": "id", "value": "no-such-element"}
    else:
        _, name, attrs = best
        first_class = attrs.get("class", "").split()[:1]
        if attrs.get("id"):
            strategy = {"kind": "id", "value": attrs["id"]}
        elif first_class:
            strategy = {"kind": "css", "value": f"{name}.{first_class[0]}"}
        else:
            strategy = {"kind": "css", "value": name}
    return json.dumps(
        {"strategy": strategy, "confidence": 0.7, "reason": "Closest match by tag and text."}
    )
