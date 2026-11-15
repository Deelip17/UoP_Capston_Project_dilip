"""Deterministic stand-in for the LLM extraction step (FR-36).

Used by the mock provider so the analyzer runs offline on fixtures. It applies
simple rules to the requirement text found between the prompt delimiters and
returns JSON in the same schema a real model must produce. It deliberately rates
every requirement "Low" so the analyzer's own rule-based risk scoring is what the
tests exercise.
"""

from __future__ import annotations

import json
import re

from aitaf.analyzer.prompts import CLOSE, OPEN
from aitaf.core.llm import LlmRequest

_STORY = re.compile(
    r"^as an? (?P<actor>.+?),?\s+i want (?:to )?(?P<action>.+?)(?:\s+so that\s+(?P<outcome>.+))?$",
    re.IGNORECASE | re.DOTALL,
)
_ARTICLE_ACTOR = re.compile(r"^(?:a|an)\s+(\w+)", re.IGNORECASE)


def _requirement_text(prompt: str) -> str:
    start = prompt.rindex(OPEN) + len(OPEN)
    end = prompt.index(CLOSE, start)
    return prompt[start:end].strip()


def mock_extraction_responder(req: LlmRequest) -> str:
    text = _requirement_text(req.prompt)
    story = _STORY.match(text)
    if story:
        actors = [story.group("actor").strip()]
        actions = [story.group("action").strip().rstrip(".")]
        outcome = story.group("outcome")
        outcomes = [outcome.strip().rstrip(".")] if outcome else []
    else:
        lowered = text.lower()
        article = _ARTICLE_ACTOR.match(text)
        actors = (
            ["system"]
            if lowered.startswith("the system")
            else [article.group(1).lower() if article else "user"]
        )
        sentence = text.split(". ")[0].strip().rstrip(".")
        actions = [sentence]
        outcomes = [sentence]
    return json.dumps(
        {
            "actors": actors,
            "actions": actions,
            "preconditions": [],
            "outcomes": outcomes,
            "risk": "Low",
            "risk_rationale": "Mock extraction without model judgement.",
            "ambiguities": [],
        }
    )
