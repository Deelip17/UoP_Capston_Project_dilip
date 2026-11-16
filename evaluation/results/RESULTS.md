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

Configuration **rules v1 on the hold-out set (independent)** (57 labelled failures)

| Metric | Value | Basis |
|---|---|---|
| Classification accuracy | 75.4% (43/57) | failures whose category equals the author's label, over labelled failures |
| Failures decided by the rules | 87.7% (50/57) | failures classified by a deterministic rule, over all failures |
| Accuracy of the rule-decided failures | 76.0% (38/50) | rule-decided failures that match the label, over rule-decided failures |

| Category | Labelled | Precision | Recall |
|---|---|---|---|
| locator | 12 | 75% | 100% |
| assertion_defect | 13 | 65% | 100% |
| timing_flaky | 7 | 100% | 57% |
| environment | 11 | 100% | 73% |
| test_data | 8 | 50% | 12% |
| unknown | 6 | 71% | 83% |

Disagreements (label, analysed as, count): environment to assertion_defect: 2; environment to unknown: 1; test_data to assertion_defect: 5; test_data to locator: 1; test_data to unknown: 1; timing_flaky to locator: 3; unknown to test_data: 1

Configuration **rules v2 on the hold-out set (independent)** (57 labelled failures)

| Metric | Value | Basis |
|---|---|---|
| Classification accuracy | 80.7% (46/57) | failures whose category equals the author's label, over labelled failures |
| Failures decided by the rules | 87.7% (50/57) | failures classified by a deterministic rule, over all failures |
| Accuracy of the rule-decided failures | 82.0% (41/50) | rule-decided failures that match the label, over rule-decided failures |

| Category | Labelled | Precision | Recall |
|---|---|---|---|
| locator | 12 | 100% | 75% |
| assertion_defect | 13 | 76% | 100% |
| timing_flaky | 7 | 64% | 100% |
| environment | 11 | 100% | 82% |
| test_data | 8 | 75% | 38% |
| unknown | 6 | 71% | 83% |

Disagreements (label, analysed as, count): environment to assertion_defect: 1; environment to unknown: 1; locator to timing_flaky: 3; test_data to assertion_defect: 3; test_data to timing_flaky: 1; test_data to unknown: 1; unknown to test_data: 1

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
| Script executability | 0.0% (0/30) | scripts that ran their steps without a missing element or runtime error (passed, or failed on an assertion), over scripts generated |
| Script pass rate | 0.0% (0/30) | generated scripts that passed on the unmutated shop, over scripts generated |
| Locator validity | 0.0% (0/50) | primary locators that exist on the baseline pages, over generated locators |
| Test cases turned into scripts | 55.6% (30/54) | scripts that passed static validation and grounding, over approved test cases |
| API cost of the pipeline | $0.0312 | sum of token costs over all model calls (zero for the mock provider) |

**sg-v2 live** (provider: live, page context: yes)

| Metric | Value | Basis |
|---|---|---|
| Script executability | 33.3% (8/24) | scripts that ran their steps without a missing element or runtime error (passed, or failed on an assertion), over scripts generated |
| Script pass rate | 25.0% (6/24) | generated scripts that passed on the unmutated shop, over scripts generated |
| Locator validity | 100.0% (12/12) | primary locators that exist on the baseline pages, over generated locators |
| Test cases turned into scripts | 44.4% (24/54) | scripts that passed static validation and grounding, over approved test cases |
| API cost of the pipeline | $0.0338 | sum of token costs over all model calls (zero for the mock provider) |

## Non-LLM latency

| Metric | Value | Basis |
|---|---|---|
| Non-LLM latency (median) | 99.8 ms | report build and write on one stored run, warm-up excluded, no model calls |
| Non-LLM latency (p95) | 119.1 ms | report build and write on one stored run, warm-up excluded, no model calls |

## Limits

- The mock rows measure the pipeline and the rules, not a language model; live rows are labelled live.
- The failure labels were written by the author after the corpus was built from the author's own recipes; the figure is agreement with that judgement, not accuracy on unseen applications.
- Live rows are one run each of one small model (gpt-4o-mini); with analyzer prompt ra-v2 (tuned on the same 20 requirements) all 54 test cases reached the script step, and the script generator rejected the plans it could not ground or re-ask. The rates are for that run, not for models in general.
- Rules v2 were changed after seeing the errors on the 50 development failures, so their score on those 50 is not independent; only the hold-out rows are.
- Test cases were approved by the harness, not by a reviewer.
- One demo application and one live run per configuration: no confidence intervals.
