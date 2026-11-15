# diagnosis

The Failure Analyzer: it explains why stored tests failed, in the same words every time, and groups failures that look alike (FR-27 to FR-30). It works from stored results, so it can be run long after the execution.

Steps, cheapest first:

1. **Rules** (`rules`): ordered, deterministic checks of the exception type, the short exception text and the log decide the clear cases: environment (network errors, refused connections, closed browser, 5xx), assertion (an application defect, even if the message mentions a missing element), locator (including the page object's own "no locator strategy matched" message), test data (missing keys or files, conflicts), timing (timeouts that are not waiting for a locator). Each verdict has a cause, a next step and a confidence.
2. **Model** (`prompt`, `mock_responder`): only a failure no rule recognises. The failure is masked of secrets and personal data (emails included), cut to size, and framed as untrusted data; if any part looks like a prompt injection, nothing is sent. The answer must match a schema; one re-ask is allowed. Its confidence is capped at 0.8 and the analysis names the model and prompt version (NFR-30).
3. **Fallback**: no gateway, a refused or invalid answer, a provider outage or a reached call cap give a labelled `fallback` analysis (category unknown, confidence 0.3), never an error.
4. **Clusters** (`signature`): the exception type plus the text with numbers, URLs, paths, hex ids and quoted values replaced give a cluster ID `CL-xxxxxxxx`; failures with the same signature share it.

| Module | Purpose | Requirements |
|---|---|---|
| `rules` | `FailureFacts`, `Verdict`, `classify` | FR-27, FR-28 |
| `signature` | `normalise_text`, `cluster_id` | FR-29 |
| `prompt`, `mock_responder` | Masked, framed prompt; answer schema; DOM text snippet; deterministic offline answer | FR-28, FR-30, NFR-10, NFR-13 |
| `analyzer` | `FailureAnalyzer.analyze(run_id)`: one stored `FailureAnalysis` per failed or errored test, with evidence references (log, screenshot, DOM snapshot, healing events) | FR-27 to FR-30, NFR-30, NFR-35 |

## Use

```text
aitaf diagnose [--run RUN_ID] [--evidence reports/runs] [--no-llm]
```

Prints each failure with category, confidence, cluster, cause, next step and evidence, then a summary. Repeating the command replaces the stored analyses (the ID is derived from the test result).

## Tests

`tests/unit/diagnosis/`: a labelled fixture table for every rule (these are unit-test fixtures written with the rules, **not** the evaluation set for objective O4), signature and prompt tests including seeded secrets and injections, the analyzer on stored results with a real gateway and mock provider (model labelling, fallbacks, captured payload), and the command line over a real execute-then-diagnose chain.

## Not built

- Classification accuracy against an independently labelled set (objective O4) is not measured yet; the rules and the confidence values are initial, written by the same author as the unit-test fixtures.
- The rules know English phrases from Playwright, Selenium, PyTest, Python and browsers; other tools' messages fall to the model or the fallback.
- A test that failed on an early attempt and passed on a retry is not analysed (only the final failed or errored result is stored), so flakiness is judged only from timeouts and repeated attempts.
- The model sees text, not the screenshot: the screenshot is only referenced.
- Offline, the "model" is a deterministic mock that answers `unknown` or `timing_flaky`; real model quality has not been measured.
- Confidence is a rule-strength score, not a calibrated probability.
