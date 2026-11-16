# How to label the failure corpus (your task, before the classifier runs)

The Failure Analyzer is scored against labels that **you** write, so the score means something. This only works if you label first and the analyzer has not seen these failures.

## Rules

1. Do not run `aitaf diagnose` or `aitaf evaluate classify` until every label is filled in. The scorer refuses a corpus the analyzer has already seen.
2. Do not read `src/aitaf/diagnosis/rules.py` while labelling. Decide from your own judgement of what a tester would conclude.
3. Label from the evidence only: `evaluation/corpus/failures_to_label.csv` (error type, error text, the test source, the screenshot name) and, if you want, the screenshots and page snapshots in `evaluation/corpus/evidence/`.
4. Write one category per row in the `category` column of `evaluation/corpus/labels.csv`. Do not change the `tc_id` column. All 50 rows must be filled in.
5. If you are unsure, pick the most useful category for a tester and note it in your own scratch notes (optional). Use `unknown` only when none of the five fits or you really cannot tell. Do not go back and change labels after you have seen the scores.

## The six categories (use exactly these words)

| Category | Meaning |
|---|---|
| `locator` | The test could not find an element because the selector no longer matches the page. The page may have changed, or the selector is wrong. |
| `assertion_defect` | The test reached its check, and the check failed because the actual value differs from the expected value. This is a defect in the application or in the test's expectation. |
| `timing_flaky` | An operation waited too long, or the failure depends on timing, so a retry could pass. |
| `environment` | The application, server, network or browser could not be reached, or access was blocked. |
| `test_data` | The input data was rejected or invalid, so the flow did not go on as planned. |
| `unknown` | None of the above fits, or you cannot tell from the evidence. |

## Afterwards

1. Commit `labels.csv` before running anything else (the commit time proves the order).
2. Run `aitaf evaluate classify` (rules only), then `aitaf evaluate classify --llm` (rules and model).
3. Optional but valuable: ask one other person to label 20 of the failures independently, and report how often you agree.
