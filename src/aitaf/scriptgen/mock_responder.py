"""Deterministic stand-in for the LLM automation-planning step (FR-36).

Returns a schema-valid plan (page, three locators with two fallbacks each, and a
short step list) for any test case, using the first synthetic data value if one
is supplied, so the Script Generator runs offline and in CI.
"""

from __future__ import annotations

import json
import re

from aitaf.core.llm import LlmRequest
from aitaf.scriptgen.catalogue import BLOCK_CLOSE, BLOCK_OPEN
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


_ELEMENT = re.compile(r"^ELEMENT (\S+) tag=(\S+) kind=(\S+)(.*)$")
_ATTR = re.compile(r'(type|id|class|data-qa)=(\S+)|text="([^"]*)"')
_WORDS = re.compile(r"[a-z0-9]+")
_STOP = frozenset({"the", "a", "an", "to", "of", "and", "in", "on", "is", "for", "with", "that"})


def _catalogue(prompt: str) -> tuple[str, list[tuple[str, str]], list[dict[str, str]]] | None:
    """(app, [(page, path)], elements in order) parsed from the catalogue block, or None."""
    if BLOCK_OPEN not in prompt:
        return None
    start = prompt.rindex(BLOCK_OPEN) + len(BLOCK_OPEN)
    block = prompt[start : prompt.index(BLOCK_CLOSE, start)]
    app, pages, elements = "app", [], []
    for line in block.splitlines():
        if line.startswith("APP "):
            app = line[4:].strip()
        elif line.startswith("PAGE "):
            _, name, path = line.split(" ", 2)
            pages.append((name, path.removeprefix("path=")))
        else:
            m = _ELEMENT.match(line)
            if m:
                attrs = {"name": m[1], "tag": m[2], "kind": m[3], "page": pages[-1][0]}
                for found in _ATTR.finditer(m[4]):
                    if found[3] is not None:
                        attrs["text"] = found[3]
                    else:
                        attrs[found[1]] = found[2]
                elements.append(attrs)
    return app, pages, elements


def _words(text: str) -> set[str]:
    return {w for w in _WORDS.findall(text.lower().replace("_", " ")) if w not in _STOP}


def _strategies(el: dict[str, str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if el.get("id"):
        out.append({"kind": "id", "value": el["id"]})
    if el.get("class"):
        out.append({"kind": "css", "value": f"{el['tag']}.{el['class']}"})
    if el.get("data-qa"):
        out.append({"kind": "xpath", "value": f"//{el['tag']}[@data-qa='{el['data-qa']}']"})
    if el.get("text") and el["kind"] != "input":
        out.append({"kind": "text", "value": el["text"]})
    return out


def _catalogue_plan(
    prompt: str, parsed: tuple[str, list[tuple[str, str]], list[dict[str, str]]]
) -> str:
    """A grounded plan: reach the page the case is about, act on matching elements, assert."""
    app, pages, elements = parsed
    start = prompt.rindex(OPEN) + len(OPEN)
    record = prompt[start : prompt.index(CLOSE, start)]
    # the title is generic ("Verify that ..."); the steps and expected results name the page
    case = _words(
        " ".join(ln for ln in record.splitlines() if ln.startswith(("Steps:", "Expected:")))
    )
    score = {e["name"]: len(case & _words(f"{e['name']} {e.get('text', '')}")) for e in elements}
    paths = dict(pages)
    order = [name for name, _ in pages]
    page_score = {
        page: sum(score[e["name"]] for e in elements if e["page"] == page)
        + (2 if page in case else 0)
        for page in order
    }
    target = max(order, key=lambda page: (page_score[page], -order.index(page)))
    value = _first_data_value(prompt)

    def on(page: str) -> list[dict[str, str]]:
        return [e for e in elements if e["page"] == page]

    used: list[dict[str, str]] = []
    steps: list[dict[str, str]] = [{"action": "open", "value": paths[order[0]]}]

    def act(el: dict[str, str]) -> None:
        if el not in used:
            used.append(el)
        if el["kind"] == "input":
            steps.append({"action": "type", "target": el["name"], "value": value})
        elif el["kind"] == "text":
            steps.append({"action": "assert_visible", "target": el["name"]})
        else:
            steps.append({"action": "click", "target": el["name"]})

    for page in order[: order.index(target)]:  # reach the target page
        items = on(page)
        for el in (e for e in items if e["kind"] == "input"):
            act(el)
        buttons = [e for e in items if e["kind"] == "button"]
        if buttons:
            # a page of look-alike buttons (Add ..., Add ...) offers items: take the first;
            # otherwise the last button moves the flow on (Remove ..., Proceed ...)
            same = len({b.get("text", "").split(" ")[0] for b in buttons}) == 1
            act(buttons[0] if same else buttons[-1])
        links = [e for e in items if e["kind"] == "link"]
        if links:
            act(links[0])
    wanted = [e for e in on(target) if score[e["name"]]] or on(target)[:1]
    for el in wanted:
        act(el)
    following = order.index(target) + 1
    if steps[-1]["action"] == "click" and following < len(order) and on(order[following]):
        el = on(order[following])[0]
        used.append(el)
        steps.append({"action": "assert_visible", "target": el["name"]})
    elif steps[-1]["action"] != "assert_visible":
        steps.append({"action": "assert_visible", "target": wanted[-1]["name"]})
    locators = [
        {"name": e["name"], "primary": s[0], "fallbacks": s[1:]}
        for e in used
        if (s := _strategies(e))
    ]
    return json.dumps({"page": app, "locators": locators, "steps": steps})


def mock_script_responder(req: LlmRequest) -> str:
    parsed = _catalogue(req.prompt)
    if parsed is not None and parsed[2]:
        return _catalogue_plan(req.prompt, parsed)
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
