"""Results table and charts from the raw evaluation files (FR-39, objective O7).

Reads the CSV files written by ``aitaf evaluate`` and writes ``RESULTS.md`` (every figure
with its counts and basis, mock and live labelled separately) and three charts as PNG.
Charts need matplotlib, an optional extra (``pip install -r requirements-report.txt``);
the table does not. Colours are slots 1 and 2 of the reference categorical palette on a
light surface, values are printed on the bars, and every series has a legend entry.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from aitaf.core.errors import ConfigError
from aitaf.evaluation.classify_eval import (
    ClassificationRow,
    classification_figures,
    confusion,
    per_category,
    read_rows_csv,
)
from aitaf.evaluation.generation_eval import GenerationTrial, read_generation_csv
from aitaf.evaluation.healing_eval import HealingTrial, read_trials_csv
from aitaf.evaluation.latency_eval import LatencySample, read_latency_csv
from aitaf.evaluation.summary import (
    Figure,
    generation_figures,
    healing_by_kind,
    healing_figures,
    latency_figures,
)

BLUE, ORANGE = "#2a78d6", "#eb6834"
SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#52514e"


def format_figure(figure: Figure) -> str:
    if figure.value is None:
        return "n/a"
    if figure.unit == "ratio":
        return f"{figure.value * 100:.1f}% ({figure.numerator}/{figure.denominator})"
    if figure.unit == "usd":
        return f"${figure.value:.4f}"
    return f"{figure.value:.1f} {figure.unit}"


def _table(figures: Sequence[Figure]) -> list[str]:
    lines = ["| Metric | Value | Basis |", "|---|---|---|"]
    lines += [f"| {f.label} | {format_figure(f)} | {f.basis} |" for f in figures]
    return lines


def build_markdown(
    healing: Sequence[HealingTrial],
    classification: Mapping[str, Sequence[ClassificationRow]],
    generation: Sequence[GenerationTrial],
    latency: Sequence[LatencySample],
) -> str:
    """All figures as one Markdown document; every section says what it is based on."""
    out = ["# Evaluation results", ""]
    out += ["## Healing (seeded mutations of the sample shop)", ""]
    out += _table(healing_figures(healing)) + [""]
    out += ["| Mutation kind | Trials | Repaired | Repaired correctly |", "|---|---|---|---|"]
    out += [f"| {k} | {n} | {r} | {c} |" for k, n, r, c in healing_by_kind(healing)] + [""]
    out += ["## Failure classification (against the author's labels)", ""]
    for name, rows in classification.items():
        out += [f"Configuration **{name}** ({len(rows)} labelled failures)", ""]
        out += _table(classification_figures(rows)) + [""]
        out += ["| Category | Labelled | Precision | Recall |", "|---|---|---|---|"]
        for category, count, precision, recall in per_category(rows):
            p = "n/a" if precision is None else f"{precision * 100:.0f}%"
            r = "n/a" if recall is None else f"{recall * 100:.0f}%"
            out.append(f"| {category} | {count} | {p} | {r} |")
        wrong = sorted((k, v) for k, v in confusion(rows).items() if k[0] != k[1])
        out += ["", "Disagreements (label, analysed as, count): "]
        out[-1] += "; ".join(f"{a} to {b}: {n}" for (a, b), n in wrong) or "none"
        out.append("")
    out += ["## Script generation (run in Chromium on the unmutated shop)", ""]
    for trial in generation:
        out += [
            f"**{trial.config}** (provider: {trial.provider}, page context: "
            f"{'yes' if trial.page_context else 'no'})",
            "",
        ]
        out += _table(generation_figures(trial)) + [""]
    out += ["## Non-LLM latency", ""] + _table(latency_figures(latency)) + [""]
    out += [
        "## Limits",
        "",
        "- The mock rows measure the pipeline and the rules, not a language model; live rows are "
        "labelled live.",
        "- The failure labels were written by the author after the corpus was built from the "
        "author's own recipes; the figure is agreement with that judgement, not accuracy on "
        "unseen applications.",
        "- Live rows rest on very few scripts (the live model flagged 17 of the 18 requirements "
        "that were written to be clear as ambiguous, so only 2 to 3 test cases were left to "
        "script): they show that the pipeline works with a live model, not a rate.",
        "- Rules v2 were changed after seeing the errors on the 50 development failures, so "
        "their score on those 50 is not independent; only the hold-out rows are.",
        "- Test cases were approved by the harness, not by a reviewer.",
        "- One demo application and one live run per configuration: no confidence intervals.",
        "",
    ]
    return "\n".join(out)


def _pyplot() -> Any:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ConfigError("charts need matplotlib: pip install -r requirements-report.txt") from exc
    return plt


def _style(ax, title: str, ylabel: str) -> None:  # type: ignore[no-untyped-def]
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.set_ylim(0, 112)
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED)


def _bars(ax, groups, series) -> None:  # type: ignore[no-untyped-def]
    """Grouped bars: ``series`` is [(label, colour, [value or None per group])]."""
    width = 0.8 / len(series)
    for i, (label, colour, values) in enumerate(series):
        xs = [g + i * width - 0.4 + width / 2 for g in range(len(groups))]
        shown = [0 if v is None else v for v in values]
        bars = ax.bar(xs, shown, width * 0.92, color=colour, label=label, edgecolor=SURFACE)
        for bar, v in zip(bars, values, strict=True):
            ax.annotate(
                "n/a" if v is None else f"{v:.0f}",
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                ha="center",
                va="bottom",
                fontsize=8,
                color=INK,
                xytext=(0, 2),
                textcoords="offset points",
            )
    ax.set_xticks(range(len(groups)), groups)
    if len(series) > 1:
        ax.legend(
            frameon=False,
            fontsize=8,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.3),
            ncols=len(series),
        )


def write_charts(
    folder: Path | str,
    healing: Sequence[HealingTrial],
    classification: Sequence[ClassificationRow],
    generation: Sequence[GenerationTrial],
) -> list[Path]:
    """Write three PNG charts into ``folder`` and return their paths."""
    plt = _pyplot()
    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    paths = []

    kinds = healing_by_kind(healing)
    fig, ax = plt.subplots(figsize=(6, 3.6), facecolor=SURFACE)
    _bars(
        ax,
        [f"{k}\n(n={n})" for k, n, _, _ in kinds],
        [("Repaired correctly", BLUE, [100 * c / n for _, n, _, c in kinds])],
    )
    _style(
        ax, "Healing: share of broken locators repaired correctly, by kind of change", "% of trials"
    )
    paths.append(target / "healing_by_kind.png")
    fig.savefig(paths[-1], dpi=200, bbox_inches="tight")
    plt.close(fig)

    cats = [c for c in per_category(classification) if c[1]]  # categories that have labels
    fig, ax = plt.subplots(figsize=(7, 3.6), facecolor=SURFACE)
    _bars(
        ax,
        [f"{c.replace(chr(95), chr(10))}{chr(10)}(n={n})" for c, n, _, _ in cats],
        [
            ("Precision", BLUE, [None if p is None else 100 * p for _, _, p, _ in cats]),
            ("Recall", ORANGE, [None if r is None else 100 * r for _, _, _, r in cats]),
        ],
    )
    _style(ax, "Failure classification: precision and recall per category (rules)", "%")
    paths.append(target / "classification.png")
    fig.savefig(paths[-1], dpi=200, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.6), facecolor=SURFACE)
    _bars(
        ax,
        [f"{t.config}{chr(10)}({t.scripts} scripts)" for t in generation],
        [
            (
                "Executable scripts",
                BLUE,
                [100 * t.executable / t.scripts if t.scripts else None for t in generation],
            ),
            (
                "Locators on the real pages",
                ORANGE,
                [100 * t.valid_locators / t.locators if t.locators else None for t in generation],
            ),
        ],
    )
    _style(ax, "Script generation: without (sg-v1) and with (sg-v2) page context", "%")
    paths.append(target / "generation.png")
    fig.savefig(paths[-1], dpi=200, bbox_inches="tight")
    plt.close(fig)
    return paths


def write_results(
    results_dir: Path | str,
    charts: bool = True,
) -> list[Path]:
    """Read the raw CSVs in ``results_dir`` and write RESULTS.md (and the charts)."""
    folder = Path(results_dir)
    healing = read_trials_csv(folder / "healing.csv")
    variants = (
        ("rules v1 (first run, dev set of 50)", "rules"),
        ("rules v1 + mock model (dev set)", "rules_model"),
        ("rules v2, tuned on the same 50 labels (NOT independent)", "v2_dev_rules"),
        ("rules v1 on the hold-out set (independent)", "holdout_v1_rules"),
        ("rules v2 on the hold-out set (independent)", "holdout_v2_rules"),
    )
    classification = {
        name: read_rows_csv(folder / f"classification_{key}.csv")
        for name, key in variants
        if (folder / f"classification_{key}.csv").exists()
    }
    generation = read_generation_csv(folder / "generation.csv")
    latency = read_latency_csv(folder / "latency.csv")
    written = [folder / "RESULTS.md"]
    written[0].write_text(
        build_markdown(healing, classification, generation, latency), encoding="utf-8", newline="\n"
    )
    if charts:
        first = next(iter(classification.values()), [])
        written += write_charts(folder / "charts", healing, first, generation)
    return written
