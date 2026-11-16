# evaluation

The evaluation harness: it runs the framework against the sample shop and writes raw CSV files from which every reported figure can be recomputed (FR-38, FR-39, NFR-01, NFR-03). It is a tool, like the command line, so it may import any component; the import-rule check still forbids it from importing a browser or database library.

| Module | Purpose | Requirements |
|---|---|---|
| `healing_eval` | One trial per seeded mutation (at least 30 of the 37): the healer gets the baseline signature, the mutated page and only the locator of the mutated kind, with no stored fallbacks. Ground truth is the shop's hidden `data-gt` attribute, which the healer never sees. Ten control trials ask for a repair where the element is absent (the right answer is no repair). Raw CSV in and out | FR-24, FR-26, FR-38, NFR-03 |
| `corpus` | Builds a corpus of about fifty real failures in Chromium (numbered tests, no category in names or data), scrubs local paths, writes `failures_to_label.csv` and a blank `labels.csv`; the analyzer is never run on it here | FR-27, FR-28 |
| `classify_eval` | Reads and checks the author's labels (all six categories, at least 40, every failure labelled), refuses a corpus the analyzer has already seen, scores rules only and rules plus model on throw-away copies; accuracy, per-category precision and recall, confusion counts, SHA-256 of the labels | FR-27, FR-28, NFR-15 |
| `commands` | `aitaf evaluate` with `heal`, `corpus` and `classify` | FR-35 |
| `summary` | Figures with their counts: healing success, accuracy, precision, false-heal rate, control rejection, decision time (median, p95) | FR-39, NFR-01 |

The same seed selects the same mutations (`select_mutations`); every figure states its numerator and denominator.

## Not built

- This first part measures the healer's decision on a page snapshot, without a browser; the end-to-end run in Chromium is shown separately (the Unit 6 healing evidence).
- Script generation and latency evaluations, charts and the results table are added in the following parts of the slice.
- The corpus failures are produced by recipes the author wrote, then labelled by the author: it measures agreement with the author's judgement on this kind of failure, not accuracy on unseen applications. A second labeller is optional and not yet arranged.
- Healing is scored on the similarity rungs without a browser; the model step is available with `--llm` (mock by default).
