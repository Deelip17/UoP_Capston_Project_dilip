"""Script Generator (FR-12 to FR-16, FR-30, NFR-10, NFR-11, NFR-13, NFR-30).

Per approved test case: mask -> one LLM call returning a structured plan -> schema
validation (one re-ask) -> template rendering -> static validation. A script that
fails validation is rejected and never saved. Accepted scripts, one page object
and locator repository per page, and a ``conftest.py`` are written together under
the output directory, and the manifest and records are persisted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from aitaf.core.errors import LlmValidationError, PolicyError
from aitaf.core.llm import LlmGateway, LlmRequest
from aitaf.core.logging import current_run_id, get_logger
from aitaf.core.masking import find_injection, mask, validate_llm_json
from aitaf.core.metrics import Metrics, timed
from aitaf.core.models import Locator, LocatorStrategy, Script, TestCase, TestData
from aitaf.core.storage import Repository
from aitaf.scriptgen import templates
from aitaf.scriptgen.catalogue import PageCatalogue
from aitaf.scriptgen.files import safe_write
from aitaf.scriptgen.plan import PlanSchema, StrategySchema
from aitaf.scriptgen.prompts import (
    PROMPT_VERSION,
    PROMPT_VERSION_CATALOGUE,
    build_prompt,
    build_reask_prompt,
)
from aitaf.scriptgen.validator import assert_valid, validate_script

COMPONENT = "script_generator"

_log = get_logger(__name__)


@dataclass
class _Accepted:
    case: TestCase
    plan: PlanSchema
    model: str
    ident: str
    source: str


@dataclass
class ScriptGenerationResult:
    """Outcome of one script-generation pass."""

    scripts: list[Script] = field(default_factory=list)
    locators: list[Locator] = field(default_factory=list)
    rejected: list[tuple[str, list[str]]] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _record(case: TestCase, data: TestData | None, framework: str) -> str:
    lines = [
        f"Test case ID: {_one_line(case.tc_id)}",
        f"Title: {_one_line(case.title)}",
        f"Preconditions: {_one_line('; '.join(case.preconditions))}",
        f"Steps: {_one_line('; '.join(case.steps))}",
        f"Expected: {_one_line('; '.join(case.expected))}",
        f"Target framework: {framework}",
    ]
    if data and data.dataset:
        pairs = "; ".join(f"{_one_line(k)}={_one_line(v)}" for k, v in data.dataset.items())
        lines.append(f"Data: {pairs}")
    return "\n".join(lines)


def _strategy(item: StrategySchema) -> LocatorStrategy:
    return LocatorStrategy(kind=item.kind, value=item.value)


class ScriptGenerator:
    """Turns approved test cases into validated, maintainable PyTest scripts."""

    def __init__(
        self,
        gateway: LlmGateway,
        repo: Repository,
        framework: templates.Framework,
        base_url: str,
        allowed_hosts: frozenset[str],
        output_dir: Path,
        metrics: Metrics | None = None,
        catalogue: PageCatalogue | None = None,
    ) -> None:
        host = (urlparse(base_url).hostname or "").lower()
        hosts = frozenset(h.lower() for h in allowed_hosts)
        if host not in hosts:
            raise PolicyError(
                f"base URL host {host!r} is not on the allow-list {sorted(hosts)} (FR-21)"
            )
        self._gateway = gateway
        self._repo = repo
        self._framework = framework
        self._base_url = base_url
        self._hosts = hosts
        self._out = Path(output_dir)
        self._metrics = metrics
        self._catalogue = catalogue
        self._block: str | None = None
        self._version = PROMPT_VERSION
        if catalogue is not None:
            block = catalogue.render_block()
            matched = find_injection(block)
            if matched:
                raise PolicyError(
                    f"page snapshots contain possible prompt injection ({', '.join(matched)})"
                )
            if mask(block, keep_synthetic=True).text != block:
                raise PolicyError("page snapshots contain data that masking would alter (NFR-10)")
            self._block = block
            self._version = PROMPT_VERSION_CATALOGUE

    def generate(
        self,
        cases: list[TestCase],
        test_data: list[TestData] | None = None,
    ) -> ScriptGenerationResult:
        with timed(self._metrics, COMPONENT, "generate") as probe:
            result = self._generate(cases, test_data)
            probe.detail = f"{len(result.scripts)} scripts, {len(result.rejected)} rejected"
            return result

    def _generate(
        self,
        cases: list[TestCase],
        test_data: list[TestData] | None,
    ) -> ScriptGenerationResult:
        result = ScriptGenerationResult()
        data = {d.tc_id: d for d in test_data or []}
        accepted: list[_Accepted] = []
        used: set[str] = set()
        for case in cases:
            record = _record(case, data.get(case.tc_id), self._framework)
            matched = find_injection(record)
            if matched:
                reason = f"possible prompt injection ({', '.join(matched)})"
                _log.warning("rejected %s: %s", case.tc_id, reason)
                result.rejected.append((case.tc_id, [reason]))
                continue
            try:
                plan, model, problems = self._extract(mask(record, keep_synthetic=True).text)
            except LlmValidationError as exc:
                reason = f"model output invalid after one re-ask ({exc})"
                _log.warning("rejected %s: %s", case.tc_id, reason)
                result.rejected.append((case.tc_id, [reason]))
                continue
            if problems:
                _log.warning("rejected %s: plan not grounded in the pages", case.tc_id)
                result.rejected.append((case.tc_id, problems))
                continue
            ident = templates.identifier(case.tc_id)
            suffix = 1
            while ident in used:
                suffix += 1
                ident = f"{templates.identifier(case.tc_id)}_{suffix}"
            source = templates.render_test(self._framework, case, plan, ident, model, self._version)
            problems = validate_script(source, self._hosts)
            if problems:
                _log.warning("rejected %s: failed static validation", case.tc_id)
                result.rejected.append((case.tc_id, problems))
                continue
            used.add(ident)
            accepted.append(_Accepted(case, plan, model, ident, source))

        if not accepted:
            return result
        self._write_all(accepted, result)
        return result

    def _extract(self, record: str) -> tuple[PlanSchema, str, list[str]]:
        """Plan, model and grounding problems (empty unless a catalogue rejected the plan)."""
        prompt = build_prompt(record, self._block)
        for attempt in range(2):
            response = self._gateway.complete(
                LlmRequest(component=COMPONENT, prompt_version=self._version, prompt=prompt)
            )
            try:
                plan = validate_llm_json(response.text, PlanSchema)
            except LlmValidationError as exc:
                _log.warning("script plan invalid (attempt %d): %s", attempt + 1, exc)
                if attempt == 1:
                    raise
                prompt = build_reask_prompt(record, str(exc), self._block)
                continue
            problems = self._catalogue.check_plan(plan) if self._catalogue else []
            if not problems or attempt == 1:
                return plan, response.model, problems
            _log.warning("script plan not grounded (attempt 1): %s", "; ".join(problems))
            prompt = build_reask_prompt(record, "; ".join(problems), self._block)
        raise AssertionError("unreachable")  # pragma: no cover

    def _write_all(self, accepted: list[_Accepted], result: ScriptGenerationResult) -> None:
        pages: dict[str, dict[str, Locator]] = {}
        for item in accepted:
            page = pages.setdefault(item.plan.page, {})
            for loc in item.plan.locators:
                if loc.name in page:
                    continue
                page[loc.name] = Locator(
                    loc_id=f"{item.plan.page}.{loc.name}",
                    page=item.plan.page,
                    name=loc.name,
                    primary=_strategy(loc.primary),
                    fallbacks=[_strategy(f) for f in loc.fallbacks],
                    model=item.model,
                    prompt_version=self._version,
                )

        files: dict[str, str] = {
            "conftest.py": templates.render_conftest(self._framework, self._base_url),
            "locators/__init__.py": "",
            "pages/__init__.py": "",
        }
        for page_name, locators in pages.items():
            files[f"locators/{page_name}_locators.py"] = templates.render_locators(
                page_name, list(locators.values())
            )
            files[f"pages/{page_name}_page.py"] = templates.render_page_object(
                self._framework, page_name
            )
        scripts: list[Script] = []
        for item in accepted:
            rel = f"tests/test_{item.ident}.py"
            files[rel] = item.source
            scripts.append(
                Script(
                    script_id=f"SCR-{item.case.tc_id}",
                    tc_id=item.case.tc_id,
                    framework=self._framework,
                    path=rel,
                    validation_result="passed",
                    model=item.model,
                    prompt_version=self._version,
                )
            )

        for rel, text in files.items():
            if rel.endswith(".py"):
                assert_valid(text, self._hosts, name=rel)
        manifest = json.dumps([s.model_dump(mode="json") for s in scripts], indent=2)
        for rel, text in {**files, "manifest.json": manifest}.items():
            result.files.append(safe_write(self._out, rel, text))

        run_id = current_run_id()
        result.scripts = scripts
        result.locators = [loc for page in pages.values() for loc in page.values()]
        for script in scripts:
            self._repo.add_script(run_id, script)
        for locator in result.locators:
            self._repo.add_locator(run_id, locator)
