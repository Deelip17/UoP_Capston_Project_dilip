# reporting

The Reporting Engine: it turns the stored data of a run into one report that opens offline, and computes the Unit 6 metrics (FR-31, FR-32, FR-34, FR-39, NFR-29).

One data model (`model`) feeds every output, so the HTML and Markdown files cannot disagree: figures are formatted by a single function. Two runs are joined by test case ID: the **execution run** (results, healing events, failure analyses) and the **source run** that analysed the requirements, generated the test cases and wrote the scripts.

| Module | Purpose | Requirements |
|---|---|---|
| `model` | `ReportData`, `ReportTest`, `TraceRow`, `MetricValue`, `format_value` | FR-31, FR-32 |
| `builder` | `build_report`; `trace_for_result` and `trace_for_requirement` return the chain requirement, test case, script, execution, failure (and the reverse) | FR-34 |
| `metrics` | `compute_metrics`: pass rate, requirement coverage, script executability, healing success rate, classification accuracy against supplied labels, generation, LLM and non-LLM latency, API cost per run; each with its unit and basis; `provider_label` says mock, live or mixed | FR-39, FR-26, NFR-01 |
| `render_html` | One offline file: summary first, then metrics, results, failure analysis (cause, next step, screenshot, log), self-healing events, traceability, notes and limits; no scripts, no external links, escaped text, status written as words, alt text, table captions, AA contrast palette | FR-31, NFR-29 |
| `render_markdown` | The same content as Markdown | FR-32 |
| `writer` | `write_report`: files into one folder (`report.html`, `report.md`, `metrics.json`, `metrics.csv`, `logs/`, `evidence/`); only evidence that exists, with safe names, is copied and linked; the PDF comes from an injected renderer | FR-31, FR-32, FR-39 |

## Use

```text
aitaf report [--run RUN_ID] [--source-run RUN_ID] [--evidence reports/runs] [--out DIR] [--labels labels.csv] [--pdf]
```

`--labels` is a CSV with the columns `tc_id,category` made by hand; it is the only way to get a classification accuracy. `--pdf` prints the HTML with headless Chromium (`aitaf.execution.pdf`, the package that owns the browser library, passed in as a function so this package imports no browser).

## Tests

`tests/unit/reporting/`: every metric checked against hand-worked values from a seeded set of records; the traceability queries; the HTML checklist (offline, escaped, summary first, text alternatives, captions, colour contrast computed from the palette); identical figures in HTML and Markdown; file writing with confined evidence; the PDF hook; the command line over a real execute, diagnose, report chain. `tests/integration/test_report_pdf.py` prints a real PDF with Chromium.

## Not built

- The Dashboard (trends over several runs, charts) is a separate slice; this report covers one run.
- The numbers are only as good as the stored data: a run whose scripts were written by hand, or whose cases were never approved, gives coverage and executability figures that say nothing about the generator. Read each metric's basis.
- Non-LLM latency (NFR-01) needs repeated rendering samples; one report has none, so it shows n/a until the evaluation slice records them.
- False-heal rate needs ground truth from the mutation harness and is not computed here.
- Classification accuracy is n/a without a hand-made labels file; the labels must be written before the classifier runs on them.
- The PDF is the browser's print of the HTML, not a separately designed document; it needs Chromium.
- Screenshots are linked, not embedded: the report folder must stay together.
