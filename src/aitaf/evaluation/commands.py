"""The ``aitaf evaluate`` command group (FR-35, FR-39).

``heal``      healing trials over the seeded mutations, raw CSV and figures;
``corpus``    build the failure corpus (real Chromium) and the blank labels file;
``classify``  score the Failure Analyzer against the author's labels.

The command line passes in a function that builds a gateway for a repository, so this
package never needs to know how providers are chosen.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from aitaf.core.errors import ValidationError
from aitaf.core.llm import LlmGateway
from aitaf.core.storage import Repository, SqliteRepository
from aitaf.evaluation.classify_eval import (
    classification_figures,
    confusion,
    labels_digest,
    per_category,
    run_classification,
    write_rows_csv,
)
from aitaf.evaluation.corpus import FAILURES_FILE, LABELS_FILE, build_corpus
from aitaf.evaluation.generation_eval import run_generation_trial, write_generation_csv
from aitaf.evaluation.healing_eval import run_healing_evaluation, write_trials_csv
from aitaf.evaluation.latency_eval import measure_report_latency, write_latency_csv
from aitaf.evaluation.results import write_results
from aitaf.evaluation.summary import (
    Figure,
    healing_by_kind,
    healing_figures,
    latency_figures,
)
from aitaf.sampleapp import CATALOGUE

GatewayFactory = Callable[[Repository], LlmGateway]
DEFAULT_RESULTS = "evaluation/results"
DEFAULT_CORPUS = "evaluation/corpus"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Sub-commands of ``aitaf evaluate``."""
    sub = parser.add_subparsers(dest="evaluation", required=True, metavar="evaluation")
    heal = sub.add_parser("heal", help="healing trials over the seeded locator mutations")
    heal.add_argument("--seed", type=int, default=42, help="seed that selects the mutations")
    heal.add_argument(
        "--count", type=int, default=len(CATALOGUE), help=f"mutations to use (max {len(CATALOGUE)})"
    )
    heal.add_argument("--llm", action="store_true", help="also switch on the model step")
    heal.add_argument("--out", default=f"{DEFAULT_RESULTS}/healing.csv", help="raw CSV")
    corpus = sub.add_parser("corpus", help="build the failure corpus in real Chromium")
    corpus.add_argument("--out", default=DEFAULT_CORPUS, help="new folder for the corpus")
    corpus.add_argument(
        "--set", dest="recipe_set", choices=["dev", "holdout"], default="dev", help="recipe set"
    )
    generate = sub.add_parser(
        "generate", help="run the pipeline with and without page context and execute the scripts"
    )
    generate.add_argument("--requirements", default="data/requirements/shop_requirements.md")
    generate.add_argument("--pages", default="data/dom/shop", help="baseline page snapshots")
    generate.add_argument("--live", action="store_true", help="also run both on the live model")
    generate.add_argument("--cache-dir", help="response cache for live runs")
    generate.add_argument("--out", default=f"{DEFAULT_RESULTS}/generation.csv", help="raw CSV")
    generate.add_argument("--keep-db", help="keep the database of the last mock run (for latency)")
    latency = sub.add_parser("latency", help="time the report pipeline (non-LLM latency)")
    latency.add_argument("--db", required=True, help="database with an executed run")
    latency.add_argument("--samples", type=int, default=30)
    latency.add_argument("--out", default=f"{DEFAULT_RESULTS}/latency.csv", help="raw CSV")
    results = sub.add_parser("results", help="write RESULTS.md and charts from the raw CSV files")
    results.add_argument("--dir", default=DEFAULT_RESULTS, help="folder with the raw CSV files")
    results.add_argument("--no-charts", action="store_true", help="table only (no matplotlib)")
    classify = sub.add_parser("classify", help="score the Failure Analyzer against your labels")
    classify.add_argument("--corpus", default=DEFAULT_CORPUS, help="folder made by 'corpus'")
    classify.add_argument("--labels", help=f"labels CSV (default: <corpus>/{LABELS_FILE})")
    classify.add_argument("--llm", action="store_true", help="also use the model step")
    classify.add_argument("--out", default=f"{DEFAULT_RESULTS}/classification.csv", help="raw CSV")


def _percent(figure: Figure) -> str:
    if figure.value is None:
        return "n/a"
    if figure.unit == "ratio":
        counts = (
            f" ({figure.numerator}/{figure.denominator})" if figure.denominator is not None else ""
        )
        return f"{figure.value * 100:.1f}%{counts}"
    return f"{figure.value:.2f} {figure.unit}"


def _heal(args: argparse.Namespace, factory: GatewayFactory | None) -> int:
    trials = run_healing_evaluation(
        args.seed, args.count, gateway_factory=factory if args.llm else None
    )
    path = write_trials_csv(trials, args.out)
    print(f"healing evaluation: seed {args.seed}, {args.count} mutations, raw rows in {path}")
    for figure in healing_figures(trials):
        print(f"  {figure.label:<34} {_percent(figure)}")
    for kind, total, repaired, correct in healing_by_kind(trials):
        print(
            f"  mutation kind {kind:<6} {total:>2} trials, {repaired:>2} repaired, "
            f"{correct:>2} correct"
        )
    for trial in trials:
        if trial.trial_type == "mutation" and not trial.correct:
            print(
                f"  not repaired correctly: {trial.mutation_id} ({trial.reason or trial.proposed})"
            )
        if trial.trial_type == "control" and trial.healed:
            print(f"  false heal: {trial.mutation_id} -> {trial.proposed} ({trial.confidence})")
    return 0


def _corpus(args: argparse.Namespace) -> int:
    try:
        info = build_corpus(args.out, recipe_set=args.recipe_set)
    except FileExistsError as exc:
        raise ValidationError(str(exc)) from exc
    print(f"corpus built in {info.folder}: {info.failures} failures, {info.passed} passed")
    print(f"1. read {info.folder / FAILURES_FILE}")
    print(f"2. fill in the category column of {info.folder / LABELS_FILE} for every row")
    print("   (locator, assertion_defect, timing_flaky, environment, test_data or unknown)")
    print("3. only then run: aitaf evaluate classify")
    print("The analyzer has not been run on these failures and must not be before step 2.")
    return 0


def _classify(args: argparse.Namespace, factory: GatewayFactory | None) -> int:
    folder = Path(args.corpus)
    labels = Path(args.labels) if args.labels else folder / LABELS_FILE
    db = folder / "corpus.db"
    if not db.exists():
        raise ValidationError(f"no corpus in {folder.name!r}; run 'aitaf evaluate corpus' first")
    repo = SqliteRepository(db)
    try:
        run_id = repo.latest_run_with_results()
    finally:
        repo.close()
    if run_id is None:
        raise ValidationError("the corpus database holds no results")
    configurations: list[tuple[str, GatewayFactory | None]] = [("rules", None)]
    if args.llm:
        if factory is None:
            raise ValidationError("no model configured")
        configurations.append(("rules+model", factory))
    print(f"labels {labels.name} (sha256 {labels_digest(labels)[:16]}...)")
    for name, gateway_factory in configurations:
        rows = run_classification(
            db,
            run_id,
            labels,
            gateway_factory=gateway_factory,
            config=name,
            evidence_dir=folder / "evidence" / run_id,
        )
        target = Path(args.out)
        target = target.with_name(f"{target.stem}_{name.replace('+', '_')}{target.suffix}")
        write_rows_csv(rows, target)
        print(f"configuration {name}: {len(rows)} labelled failures, raw rows in {target}")
        for figure in classification_figures(rows):
            print(f"  {figure.label:<36} {_percent(figure)}")
        for category, count, precision, recall in per_category(rows):
            p = "n/a" if precision is None else f"{precision * 100:.0f}%"
            r = "n/a" if recall is None else f"{recall * 100:.0f}%"
            print(f"  {category:<17} labelled {count:>2}  precision {p:>4}  recall {r:>4}")
        wrong = {k: v for k, v in confusion(rows).items() if k[0] != k[1]}
        for (label, predicted), count in sorted(wrong.items()):
            print(f"  labelled {label} but analysed as {predicted}: {count}")
    return 0


def _generate(args: argparse.Namespace) -> int:
    configs = [("sg-v1 mock", None, False), ("sg-v2 mock", args.pages, False)]
    if args.live:
        configs += [("sg-v1 live", None, True), ("sg-v2 live", args.pages, True)]
    trials = []
    for name, pages, live in configs:
        trial = run_generation_trial(
            name,
            pages_dir=pages,
            requirements=args.requirements,
            live=live,
            cache_dir=args.cache_dir,
            keep_db=args.keep_db if name == "sg-v2 mock" else None,
        )
        trials.append(trial)
        print(
            f"{name}: {trial.scripts} scripts, {trial.rejected} rejected; "
            f"{trial.valid_locators}/{trial.locators} locators on the pages; "
            f"{trial.passed} passed, {trial.failed} failed, {trial.errors} errors; "
            f"executable {trial.executable}/{trial.scripts}; {trial.llm_calls} model calls, "
            f"${trial.cost_usd:.4f}"
        )
    print(f"raw rows in {write_generation_csv(trials, args.out)}")
    return 0


def _latency(args: argparse.Namespace) -> int:
    rows = measure_report_latency(args.db, args.samples)
    path = write_latency_csv(rows, args.out)
    figures = latency_figures(rows)
    print(f"{len(rows)} samples (first is warm-up), raw rows in {path}")
    for figure in figures:
        print(f"  {figure.label:<34} {_percent(figure)}")
    return 0


def run(args: argparse.Namespace, factory: GatewayFactory | None) -> int:
    """Run the chosen evaluation; raises :class:`ValidationError` for unusable input."""
    if args.evaluation == "heal":
        return _heal(args, factory)
    if args.evaluation == "generate":
        return _generate(args)
    if args.evaluation == "results":
        for path in write_results(args.dir, charts=not args.no_charts):
            print(f"wrote {path}")
        return 0
    if args.evaluation == "latency":
        return _latency(args)
    if args.evaluation == "corpus":
        return _corpus(args)
    return _classify(args, factory)
