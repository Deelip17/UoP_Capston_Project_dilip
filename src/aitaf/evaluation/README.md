# evaluation

The evaluation harness: it runs the framework against the sample shop and writes raw CSV files from which every reported figure can be recomputed (FR-38, FR-39, NFR-01, NFR-03). It is a tool, like the command line, so it may import any component; the import-rule check still forbids it from importing a browser or database library.

| Module | Purpose | Requirements |
|---|---|---|
| `healing_eval` | One trial per seeded mutation (at least 30 of the 37): the healer gets the baseline signature, the mutated page and only the locator of the mutated kind, with no stored fallbacks. Ground truth is the shop's hidden `data-gt` attribute, which the healer never sees. Ten control trials ask for a repair where the element is absent (the right answer is no repair). Raw CSV in and out | FR-24, FR-26, FR-38, NFR-03 |
| `corpus` | Builds a corpus of about fifty real failures in Chromium (numbered tests, no category in names or data), scrubs local paths, writes `failures_to_label.csv` and a blank `labels.csv`; the analyzer is never run on it here | FR-27, FR-28 |
| `classify_eval` | Reads and checks the author's labels (all six categories, at least 40, every failure labelled), refuses a corpus the analyzer has already seen, scores rules only and rules plus model on throw-away copies; accuracy, per-category precision and recall, confusion counts, SHA-256 of the labels | FR-27, FR-28, NFR-15 |
| `generation_eval` | Runs analyze, generate, approve and script through the command line in a fresh database for each configuration (prompt `sg-v1` without page context, `sg-v2` with it; mock and, with `--live`, a live model), executes the scripts in Chromium on the unmutated shop with sign-in open, and records executability, pass rate, locator validity, calls, tokens and cost | FR-12, FR-14, FR-16, NFR-02 |
| `latency_eval` | Times the report pipeline (no model) over repeated runs on one stored run; the first sample is flagged as warm-up | NFR-01 |
| `results` | `RESULTS.md` (every figure with counts and basis, mock and live separate) and three PNG charts (needs the optional `requirements-report.txt`) | FR-39 |
| `commands` | `aitaf evaluate` with `heal`, `corpus`, `classify`, `generate`, `latency` and `results` | FR-35 |
| `summary` | Figures with their counts: healing success, accuracy, precision, false-heal rate, control rejection, decision time (median, p95) | FR-39, NFR-01 |

The same seed selects the same mutations (`select_mutations`); every figure states its numerator and denominator.

## Not built

- This first part measures the healer's decision on a page snapshot, without a browser; the end-to-end run in Chromium is shown separately (the Unit 6 healing evidence).
- The harness approves every generated test case itself (a person would review them); one demo application; one live run per configuration, so no confidence intervals.
- Latency is the report pipeline only; healing decision time is measured separately in the healing trials.
- The corpus failures are produced by recipes the author wrote, then labelled by the author: it measures agreement with the author's judgement on this kind of failure, not accuracy on unseen applications. A second labeller is optional and not yet arranged.
- Healing is scored on the similarity rungs without a browser; the model step is available with `--llm` (mock by default).
