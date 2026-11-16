"""Healing evaluation over the seeded mutations of the sample shop (FR-24, FR-26, FR-38, NFR-03).

Each trial breaks one locator with one catalogued mutation and asks the Self-Healing
Engine for a repair, the way the Execution Engine does at run time: a baseline
signature from the approved pages, the mutated page as the failure snapshot, and
only the locator of the mutated kind, with no stored fallbacks (so the healer is
the only thing that can save the step).

Ground truth comes from the shop's oracle mode: the same mutated page rendered
with a ``data-gt`` attribute that the healer never sees. A proposed locator is
*correct* when it resolves to exactly one element and that element is the one the
mutation touched. Control trials ask for a repair of a locator whose element is not
on the page at all; the right answer is "no repair", so any proposal is a false heal.

The run is deterministic for a given seed (the sample of mutations) and needs no browser.
"""

from __future__ import annotations

import csv
import random
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from pathlib import Path

from aitaf.core.healing import FailureContext, HealStatus
from aitaf.core.llm import LlmGateway
from aitaf.core.logging import set_run_id
from aitaf.core.models import Locator, LocatorStrategy, Run, RunStatus
from aitaf.core.storage import InMemoryRepository, Repository
from aitaf.healing import (
    BaselineSnapshots,
    HealingConfig,
    SelfHealingEngine,
    find_elements,
    parse_dom,
)
from aitaf.sampleapp import CATALOGUE, ELEMENTS, PAGES, Mutation, render_page, write_snapshots

LOCATOR_KIND = {"id": "id", "class": "css", "xpath": "xpath", "text": "text"}
ERROR_TYPE = "LookupError"


@dataclass(frozen=True)
class HealingTrial:
    """One healing request and what became of it."""

    trial_id: str
    trial_type: str  # "mutation" or "control"
    mutation_id: str
    element: str
    mutation_kind: str
    locator_kind: str
    healed: bool
    correct: bool  # mutation: right element repaired; control: nothing proposed
    proposed: str
    confidence: float
    elapsed_ms: float
    reason: str


COLUMNS = tuple(f.name for f in fields(HealingTrial))


def select_mutations(seed: int, count: int) -> list[Mutation]:
    """``count`` mutations drawn from the committed catalogue, reproducible from ``seed``."""
    if not 1 <= count <= len(CATALOGUE):
        raise ValueError(f"count must be between 1 and {len(CATALOGUE)}")
    chosen = random.Random(seed).sample(range(len(CATALOGUE)), count)
    return [CATALOGUE[i] for i in sorted(chosen)]


def _locator(element: str, kind: str) -> Locator:
    spec = ELEMENTS[element].locator(kind)
    return Locator(
        loc_id=f"shop.{element}",
        page="shop",
        name=element,
        primary=LocatorStrategy(kind=spec.kind, value=spec.value),  # type: ignore[arg-type]
        fallbacks=[],
        model="evaluation",
        prompt_version="n/a",
    )


def _show(strategy: LocatorStrategy | None) -> str:
    return f"{strategy.kind}={strategy.value}" if strategy else ""


def _is_right_element(strategy: LocatorStrategy, oracle_html: str, element: str) -> bool:
    found = find_elements(parse_dom(oracle_html), strategy)
    return found is not None and len(found) == 1 and found[0].attrs.get("data-gt") == element


def run_healing_evaluation(
    seed: int = 42,
    count: int = len(CATALOGUE),
    *,
    controls: bool = True,
    gateway_factory: Callable[[Repository], LlmGateway] | None = None,
) -> list[HealingTrial]:
    """Run the trials; with a gateway factory the model step of the healer is switched on."""
    repo = InMemoryRepository()
    repo.create_run(
        Run(
            run_id="evaluation",
            started_at=datetime.now(UTC),
            status=RunStatus.RUNNING,
            provider="evaluation",
            environment="evaluation",
        )
    )
    set_run_id("evaluation")
    try:
        with tempfile.TemporaryDirectory() as folder:
            write_snapshots(folder)
            baseline = BaselineSnapshots(folder)
            engine = SelfHealingEngine(
                repo,
                HealingConfig(llm_enabled=gateway_factory is not None, max_attempts_per_run=10_000),
                gateway_factory(repo) if gateway_factory else None,
            )
            trials = [
                _mutation_trial(engine, baseline, mutation, f"H-{i:03d}")
                for i, mutation in enumerate(select_mutations(seed, count), start=1)
            ]
            if controls:
                trials += [
                    _control_trial(engine, baseline, name, f"C-{i:03d}")
                    for i, name in enumerate(ELEMENTS, start=1)
                ]
        return trials
    finally:
        set_run_id("")


def _ask(
    engine: SelfHealingEngine, baseline: BaselineSnapshots, locator: Locator, name: str, html: str
) -> tuple[LocatorStrategy | None, float, float, str, bool]:
    context = FailureContext(
        step_ref=f"evaluation:{name}",
        action="click",
        locator=locator,
        error_type=ERROR_TYPE,
        error_message=f"no locator strategy matched for {locator.name} on page shop",
        dom_html=html,
        baseline=baseline.signature_for(locator),
    )
    start = time.perf_counter()
    result = engine.heal(context)
    elapsed = (time.perf_counter() - start) * 1000
    healed = result.status is HealStatus.HEALED
    return (result.strategy if healed else None), result.confidence, elapsed, result.reason, healed


def _mutation_trial(
    engine: SelfHealingEngine, baseline: BaselineSnapshots, mutation: Mutation, trial_id: str
) -> HealingTrial:
    element = ELEMENTS[mutation.element]
    kind = LOCATOR_KIND[mutation.kind]
    locator = _locator(element.name, kind)
    mutated = render_page(element.page, [mutation.mutation_id])
    strategy, confidence, elapsed, reason, healed = _ask(
        engine, baseline, locator, trial_id, mutated
    )
    correct = bool(strategy) and _is_right_element(
        strategy,  # type: ignore[arg-type]
        render_page(element.page, [mutation.mutation_id], oracle=True),
        element.name,
    )
    return HealingTrial(
        trial_id=trial_id,
        trial_type="mutation",
        mutation_id=mutation.mutation_id,
        element=element.name,
        mutation_kind=mutation.kind,
        locator_kind=kind,
        healed=healed,
        correct=correct,
        proposed=_show(strategy),
        confidence=round(confidence, 4),
        elapsed_ms=round(elapsed, 3),
        reason=reason,
    )


def _control_trial(
    engine: SelfHealingEngine, baseline: BaselineSnapshots, name: str, trial_id: str
) -> HealingTrial:
    """Ask for a repair on the next page, where this element does not exist."""
    element = ELEMENTS[name]
    other = PAGES[(PAGES.index(element.page) + 1) % len(PAGES)]
    locator = _locator(name, "id")
    strategy, confidence, elapsed, reason, healed = _ask(
        engine, baseline, locator, trial_id, render_page(other)
    )
    return HealingTrial(
        trial_id=trial_id,
        trial_type="control",
        mutation_id=f"control-{name}-on-{other}",
        element=name,
        mutation_kind="absent",
        locator_kind="id",
        healed=healed,
        correct=not healed,
        proposed=_show(strategy),
        confidence=round(confidence, 4),
        elapsed_ms=round(elapsed, 3),
        reason=reason,
    )


def write_trials_csv(trials: Sequence[HealingTrial], path: Path | str) -> Path:
    """Raw results, one row per trial, so every figure can be recomputed."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for trial in trials:
            writer.writerow(asdict(trial))
    return target


def read_trials_csv(path: Path | str) -> list[HealingTrial]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return [
            HealingTrial(
                trial_id=row["trial_id"],
                trial_type=row["trial_type"],
                mutation_id=row["mutation_id"],
                element=row["element"],
                mutation_kind=row["mutation_kind"],
                locator_kind=row["locator_kind"],
                healed=row["healed"] == "True",
                correct=row["correct"] == "True",
                proposed=row["proposed"],
                confidence=float(row["confidence"]),
                elapsed_ms=float(row["elapsed_ms"]),
                reason=row["reason"],
            )
            for row in csv.DictReader(handle)
        ]
