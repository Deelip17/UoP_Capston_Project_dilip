# Evaluation

Raw data and results of the Unit 6 evaluation (FR-38, FR-39, NFR-01, NFR-03). The code is in `src/aitaf/evaluation/`; run it with `aitaf evaluate ...`.

| Path | What it is |
|---|---|
| `results/healing.csv` | One row per healing trial: 37 mutations of the sample shop (seed 42) and 10 controls (element absent). Figures are recomputed from this file |
| `corpus/` | The failure corpus: 50 real failures from Chromium (`corpus.db`, `evidence/`), `failures_to_label.csv` (what you read) and `labels.csv` (what you fill in) |
| `results/classification_*.csv` | Analyzer answers against your labels (rules; rules plus mock model) |
| `results/generation.csv` | Pipeline configurations (sg-v1/sg-v2, mock/live): scripts, executability, locator validity, tokens, cost |
| `results/latency.csv` | 30 timed report builds (non-LLM latency) |
| `results/RESULTS.md`, `results/charts/` | Table and charts made by `aitaf evaluate results` |
| `qualitative/` | Rubric and a blank ratings sheet for the qualitative metric |
| `corpus_holdout/` | Second corpus of 57 failures (different recipes) written after the rule changes; labels blank; to be labelled by the author, then scored with `aitaf evaluate classify --corpus evaluation/corpus_holdout --out evaluation/results/classification_holdout_v2.csv` |
| `LABELLING_GUIDE.md` | The rules for labelling the corpus before the classifier runs |

```text
aitaf evaluate heal [--seed 42] [--count 37] [--llm] [--out evaluation/results/healing.csv]
aitaf evaluate corpus [--out evaluation/corpus]          # once; needs Chromium
aitaf evaluate classify [--corpus ...] [--labels ...] [--llm]
```

The analyzer has not been run on the corpus. `classify` refuses blank or partial labels and a corpus the analyzer has already seen.
