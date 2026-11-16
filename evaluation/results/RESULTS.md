# Evaluation results

## Healing (seeded mutations of the sample shop)

| Metric | Value | Basis |
|---|---|---|
| Healing success rate | 86.5% (32/37) | mutated locators for which a repair was proposed, over mutated locators |
| Healing accuracy | 86.5% (32/37) | repairs that point at the right element (checked against the hidden ground truth), over mutated locators |
| Healing precision | 100.0% (32/32) | proposed repairs that point at the right element, over proposed repairs |
| False-heal rate | 2.1% (1/47) | repairs of the wrong element, plus repairs proposed where the element is absent, over all trials |
| Control rejection rate | 90.0% (9/10) | absent-element trials where no repair was proposed, over absent-element trials |
| Healing decision time (median) | 0.6 ms | time of one healing request (similarity rungs only; no browser) |
| Healing decision time (p95) | 1.4 ms | nearest-rank 95th percentile of the same samples |

| Mutation kind | Trials | Repaired | Repaired correctly |
|---|---|---|---|
| class | 10 | 10 | 10 |
| id | 10 | 10 | 10 |
| text | 7 | 2 | 2 |
| xpath | 10 | 10 | 10 |

## Failure classification (against the author's labels)

Configuration **rules v1 (first run, dev set of 50)** (50 labelled failures)

| Metric | Value | Basis |
|---|---|---|
| Classification accuracy | 66.0% (33/50) | failures whose category equals the author's label, over labelled failures |
| Failures decided by the rules | 94.0% (47/50) | failures classified by a deterministic rule, over all failures |
| Accuracy of the rule-decided failures | 70.2% (33/47) | rule-decided failures that match the label, over rule-decided failures |

| Category | Labelled | Precision | Recall |
|---|---|---|---|
| locator | 12 | 75% | 100% |
| assertion_defect | 10 | 53% | 100% |
| timing_flaky | 8 | 100% | 50% |
| environment | 12 | 100% | 58% |
| test_data | 8 | 0% | 0% |
| unknown | 0 | 0% | n/a |

Disagreements (label, analysed as, count): environment to assertion_defect: 1; environment to test_data: 1; environment to unknown: 3; test_data to assertion_defect: 8; timing_flaky to locator: 4

Configuration **rules v1 + mock model (dev set)** (50 labelled failures)

| Metric | Value | Basis |
|---|---|---|
| Classification accuracy | 66.0% (33/50) | failures whose category equals the author's label, over labelled failures |
| Failures decided by the rules | 94.0% (47/50) | failures classified by a deterministic rule, over all failures |
| Accuracy of the rule-decided failures | 70.2% (33/47) | rule-decided failures that match the label, over rule-decided failures |

| Category | Labelled | Precision | Recall |
|---|---|---|---|
| locator | 12 | 75% | 100% |
| assertion_defect | 10 | 53% | 100% |
| timing_flaky | 8 | 100% | 50% |
| environment | 12 | 100% | 58% |
| test_data | 8 | 0% | 0% |
| unknown | 0 | 0% | n/a |

Disagreements (label, analysed as, count): environment to assertion_defect: 1; environment to test_data: 1; environment to unknown: 3; test_data to assertion_defect: 8; timing_flaky to locator: 4

Configuration **rules v2, tuned on the same 50 labels (NOT independent)** (50 labelled failures)

| Metric | Value | Basis |
|---|---|---|
| Classification accuracy | 88.0% (44/50) | failures whose category equals the author's label, over labelled failures |
| Failures decided by the rules | 94.0% (47/50) | failures classified by a deterministic rule, over all failures |
| Accuracy of the rule-decided failures | 93.6% (44/47) | rule-decided failures that match the label, over rule-decided failures |

| Category | Labelled | Precision | Recall |
|---|---|---|---|
| locator | 12 | 100% | 100% |
| assertion_defect | 10 | 83% | 100% |
| timing_flaky | 8 | 100% | 100% |
| environment | 12 | 100% | 67% |
| test_data | 8 | 86% | 75% |
| unknown | 0 | 0% | n/a |

Disagreements (label, analysed as, count): environment to test_data: 1; environment to unknown: 3; test_data to assertion_defect: 2

## Script generation (run in Chromium on the unmutated shop)

**sg-v1 mock** (provider: mock, page context: no)

| Metric | Value | Basis |
|---|---|---|
| Script executability | 0.0% (0/54) | scripts that ran their steps without a missing element or runtime error (passed, or failed on an assertion), over scripts generated |
| Script pass rate | 0.0% (0/54) | generated scripts that passed on the unmutated shop, over scripts generated |
| Locator validity | 0.0% (0/3) | primary locators that exist on the baseline pages, over generated locators |
| Test cases turned into scripts | 100.0% (54/54) | scripts that passed static validation and grounding, over approved test cases |
| API cost of the pipeline | $0.0000 | sum of token costs over all model calls (zero for the mock provider) |

**sg-v2 mock** (provider: mock, page context: yes)

| Metric | Value | Basis |
|---|---|---|
| Script executability | 38.9% (21/54) | scripts that ran their steps without a missing element or runtime error (passed, or failed on an assertion), over scripts generated |
| Script pass rate | 38.9% (21/54) | generated scripts that passed on the unmutated shop, over scripts generated |
| Locator validity | 100.0% (12/12) | primary locators that exist on the baseline pages, over generated locators |
| Test cases turned into scripts | 100.0% (54/54) | scripts that passed static validation and grounding, over approved test cases |
| API cost of the pipeline | $0.0000 | sum of token costs over all model calls (zero for the mock provider) |

**sg-v1 live** (provider: live, page context: no)

| Metric | Value | Basis |
|---|---|---|
| Script executability | 0.0% (0/3) | scripts that ran their steps without a missing element or runtime error (passed, or failed on an assertion), over scripts generated |
| Script pass rate | 0.0% (0/3) | generated scripts that passed on the unmutated shop, over scripts generated |
| Locator validity | 0.0% (0/7) | primary locators that exist on the baseline pages, over generated locators |
| Test cases turned into scripts | 100.0% (3/3) | scripts that passed static validation and grounding, over approved test cases |
| API cost of the pipeline | $0.0037 | sum of token costs over all model calls (zero for the mock provider) |

**sg-v2 live** (provider: live, page context: yes)

| Metric | Value | Basis |
|---|---|---|
| Script executability | 50.0% (1/2) | scripts that ran their steps without a missing element or runtime error (passed, or failed on an assertion), over scripts generated |
| Script pass rate | 50.0% (1/2) | generated scripts that passed on the unmutated shop, over scripts generated |
| Locator validity | 100.0% (7/7) | primary locators that exist on the baseline pages, over generated locators |
| Test cases turned into scripts | 66.7% (2/3) | scripts that passed static validation and grounding, over approved test cases |
| API cost of the pipeline | $0.0024 | sum of token costs over all model calls (zero for the mock provider) |

## Non-LLM latency

| Metric | Value | Basis |
|---|---|---|
| Non-LLM latency (median) | 99.8 ms | report build and write on one stored run, warm-up excluded, no model calls |
| Non-LLM latency (p95) | 119.1 ms | report build and write on one stored run, warm-up excluded, no model calls |

## Limits

- The mock rows measure the pipeline and the rules, not a language model; live rows are labelled live.
- The failure labels were written by the author after the corpus was built from the author's own recipes; the figure is agreement with that judgement, not accuracy on unseen applications.
- Live rows rest on very few scripts (the live model flagged 17 of the 18 requirements that were written to be clear as ambiguous, so only 2 to 3 test cases were left to script): they show that the pipeline works with a live model, not a rate.
- Rules v2 were changed after seeing the errors on the 50 development failures, so their score on those 50 is not independent; only the hold-out rows are.
- Test cases were approved by the harness, not by a reviewer.
- One demo application and one live run per configuration: no confidence intervals.
