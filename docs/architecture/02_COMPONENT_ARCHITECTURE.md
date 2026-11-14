# 02 — Component Architecture (module specifications)

**Version:** 1.0 · **Date:** 14 Nov 2026 · **Feeds:** Unit 3 AA Q1b ("module-wise breakdown with input, output and methodology"), Report §3.3 · **Design only, no code**
**Sources:** `knowledge/MASTER_PLAN.md` §2 (canonical names), `01_SYSTEM_ARCHITECTURE.md` (overview, interactions A1–A17, gates), `SYSTEM_REQUIREMENTS/` (FR-01–39, NFR-01–35).
**Scope of this file:** the eight canonical modules in pipeline order. Cross-cutting services (Data Masking and Validation Layer, SQLite Persistence, Audit Logging, LLM Gateway) and the Pipeline Orchestrator appear as dependencies; their responsibilities are in `01_SYSTEM_ARCHITECTURE.md` §2.
**Relationship to `04_COMPONENT_ARCHITECTURE.md`:** this file is the authoritative module specification. `04` §3 holds an earlier shorter version of the same material; keep `04` for the patterns, entity-relationship model and technology notes, and treat any difference as resolved in favour of this file.

*AI-generated draft: review before submission.*

## 0. How to Read This File

| Field | Meaning |
|---|---|
| Purpose | Why the module exists and what problem it answers |
| Inputs / Outputs | Named records (data model in `05_DATA_FLOW.md` §4); who supplies and consumes them |
| Methodology | The ordered technique the module applies (what the Unit 3 rubric calls "methodologies") |
| Dependencies | Other modules, cross-cutting services, interfaces and external systems it needs |
| Related FRs / NFRs | Requirement IDs; text in the `SYSTEM_REQUIREMENTS` files |

**Common rules for every module:** it exchanges records through SQLite Persistence (not by calling other modules' internals, NFR-17); every LLM use goes through the LLM Gateway after masking; each record carries the run ID and upstream IDs (FR-34); each module emits latency and outcome counters (NFR-35); AI-generated outputs are labelled with model and prompt version (NFR-30).

## 1. Requirement Analyzer

**Purpose.** Convert raw natural-language requirements into structured, identified, risk-rated records that downstream modules can use without re-reading the source text, and stop poor requirements early.

**Inputs.**
- Requirement text from a file or the command line in plain text, Markdown or user-story format (from the Orchestrator).
- Run configuration: size limits, risk policy keywords, review mode.

**Outputs.**
- `AnalyzedRequirement` records: stable requirement ID, source reference, actors, actions, preconditions, expected outcomes, risk rating (High, Medium, Low) with rationale, ambiguity flags with reasons, prompt version, AI-generated label.
- A clarification list of flagged requirements (excluded from generation until resolved).

**Methodology.**
1. *Intake:* detect format; split into individual requirements (headings, bullet items, "As a… I want…" stories).
2. *Validation and sanitising:* enforce size and encoding limits, strip control characters, screen for prompt-injection patterns; reject and log failures (fail closed).
3. *Masking:* replace secrets and personal data with placeholders (Data Masking and Validation Layer).
4. *LLM extraction:* one request per requirement using a versioned prompt that demands JSON in a fixed schema; temperature fixed for repeatability.
5. *Schema validation:* reject or re-ask once on schema violations; never pass unvalidated output on.
6. *ID and risk assignment:* deterministic ID from source reference and content hash; risk rating from a rule-based keyword score combined with the model's rating, with the rationale stored.
7. *Ambiguity detection:* flag untestable wording (vague quantifiers, missing outcomes, contradictions).
8. *Persist and audit.*

**Dependencies.** Data Masking and Validation Layer; LLM Gateway; SQLite Persistence; Audit Logging; Pipeline Orchestrator. External: OpenAI API only through the gateway (mock/cache fallback available). Consumed by: Test Case Generator.

**Related FRs.** FR-01 (intake formats), FR-02 (validate and sanitise), FR-03 (LLM extraction), FR-04 (ID and risk rating), FR-05 (ambiguity flags); supporting FR-30 (redaction), FR-34 (traceability), FR-36 (mock fallback), FR-37 (audit).

**Related NFRs.** NFR-02 (≤ 60 s per requirement), NFR-08 (repeatability), NFR-10 (input and output validation), NFR-13 (prompt-injection resistance), NFR-15 (no sensitive data), NFR-22 (versioned prompts), NFR-30 (AI label), NFR-35 (metrics hooks).

## 2. Test Case Generator

**Purpose.** Produce traceable, reviewable test scenarios, test cases and synthetic data from analysed requirements, replacing the manual test-design effort named in the problem statement while leaving approval to a human.

**Inputs.**
- `AnalyzedRequirement` records not flagged as ambiguous (from persistence).
- Run configuration: review mode, techniques to apply, data rules.

**Outputs.**
- `TestScenario` records (type: positive, negative, boundary).
- `TestCase` records: ID, title, preconditions, steps, expected results, priority, requirement ID, review status (Pending, Approved, Rejected), AI-generated label.
- `TestData` records (synthetic only).
- Exports in JSON, CSV and Markdown, re-importable.

**Methodology.**
1. *Technique-guided prompting:* the prompt instructs equivalence partitioning, boundary-value analysis and negative paths, using the requirement's stated constraints.
2. *Scenario generation* per requirement, then *expansion* to detailed test cases with numbered steps and observable expected results.
3. *Schema validation* of every case; invalid output is rejected.
4. *De-duplication:* normalise text, compare similarity against a threshold, keep the first, report the count removed.
5. *Synthetic data:* rule-based generators for formats (names, emails, dates) plus model-suggested edge values; a pattern check confirms no real personal data.
6. *Traceability:* every case stores its requirement ID.
7. *Review gate (Gate 1):* new cases start as Pending; in review mode only Approved cases move on; every status change is logged.
8. *Coverage review:* check that roles and locales named in the requirements are represented and record gaps (NFR-32).

**Dependencies.** Requirement Analyzer (via persistence); Data Masking and Validation Layer; LLM Gateway; SQLite Persistence; Audit Logging; Orchestrator (review gate). Consumed by: Script Generator, Reporting Engine (coverage).

**Related FRs.** FR-06 (scenarios), FR-07 (test cases), FR-08 (synthetic data), FR-09 (de-duplication), FR-10 (review status and gate), FR-11 (export); supporting FR-34, FR-36, FR-37.

**Related NFRs.** NFR-02 (time budget), NFR-08, NFR-15 (synthetic data only), NFR-22, NFR-30, NFR-31 (human approval), NFR-32 (coverage and fairness review), NFR-35.

## 3. Script Generator

**Purpose.** Compile approved test cases into executable, maintainable PyTest scripts for Playwright or Selenium, with locators held centrally so they can be repaired, and with safeguards because generated code is untrusted.

**Inputs.**
- Approved `TestCase` and `TestData` records.
- Target framework (Playwright or Selenium) and base URL from configuration.
- Optional DOM snapshot of the target pages to improve locators.

**Outputs.**
- PyTest script files following a page-object pattern.
- `Locator` records per page: name, primary strategy, ordered fallback strategies (id, CSS, XPath, text/role, attributes), version.
- A generation manifest: which test case produced which script, validation result, AI label.

**Methodology.**
1. *Step modelling:* map each test step to an action in a framework-neutral step vocabulary (open, click, type, select, assert text, assert visible).
2. *Locator derivation:* from the DOM snapshot when available, otherwise from the model's proposal; record a primary and at least two fallbacks where the page offers them.
3. *Template-based generation:* a **driver adapter** (Playwright or Selenium) renders scripts from templates; the model fills structured slots (step list, locator names, expected values) instead of writing free-form code.
4. *Static validation:* parse the script, allow-list imports and calls, reject shell access, network calls outside the driver, file writes outside permitted directories and any hard-coded secret; failed scripts are not saved.
5. *Persist and register* in the manifest.

**Dependencies.** Test Case Generator (via persistence); Data Masking and Validation Layer (static checks); LLM Gateway; SQLite Persistence; Audit Logging; driver adapters for Playwright and Selenium. Consumed by: Execution Engine, Self-Healing Engine (locator repository).

**Related FRs.** FR-12 (Playwright scripts), FR-13 (Selenium scripts), FR-14 (PyTest page-object pattern), FR-15 (static validation), FR-16 (primary and fallback locators); supporting FR-25 (approved locator updates are written back here), FR-34.

**Related NFRs.** NFR-11 (least privilege for generated code), NFR-17 (modularity), NFR-21 (standalone use), NFR-22 (versioned templates and prompts), NFR-30 (AI label).

## 4. Execution Engine

**Purpose.** Run the generated scripts reliably on either automation tool against allow-listed applications, collect the evidence the report and the academic submission need, and call the Self-Healing Engine when a locator fails.

**Inputs.**
- Script set and `Locator` records (from persistence).
- Run configuration: driver, headless mode, timeouts, retries, parallel workers, allow-listed base URLs.

**Outputs.**
- `Run` record: run ID, configuration hash, environment, driver, repository commit.
- `TestResult` records: status, duration, error, log reference, retry count, "healed" flag.
- `Artifact` records: screenshots (every failure and optional checkpoints), traces or video (Playwright), DOM snapshot at failure, logs, JUnit XML, with checksums.

**Methodology.**
1. *Pre-flight:* check every target URL against the allow-list and abort the run before any browser action if one is not listed.
2. *PyTest execution:* start the selected driver; run tests with the configured workers, timeouts and retries.
3. *Evidence hooks:* a PyTest report hook captures a screenshot and DOM snapshot on failure and writes the artefact index.
4. *Locator-failure handling:* on element-not-found, stale or not-interactable errors, call the `LocatorHealer` interface (Self-Healing Engine); on success continue the step and flag the result "healed"; otherwise report the original error.
5. *Persistence:* write results incrementally so an interrupted run can be resumed or marked incomplete.
6. *Reporting hand-over:* emit JUnit XML and counters (duration, retries, overhead against a plain PyTest run).

**Dependencies.** Script Generator (via persistence); Self-Healing Engine (through the `LocatorHealer` interface defined in `core`, to avoid a circular dependency); SQLite Persistence; Audit Logging; Orchestrator. External: Playwright, Selenium, PyTest, the system under test (public demo applications only, ADR-001, ADR-005), file system for the evidence store. Consumed by: Failure Analyzer, Reporting Engine.

**Related FRs.** FR-17 (execution on both tools), FR-18 (screenshots), FR-19 (stored results), FR-20 (headless, timeouts, retries, workers), FR-21 (URL allow-list); supporting FR-22 (hand-off to healing), FR-34, FR-35 (stage run from CLI).

**Related NFRs.** NFR-04 (≤ 10% overhead), NFR-07 (durable run state), NFR-08 (repeatability), NFR-11 (isolation, allow-list), NFR-23 (parallel scaling), NFR-26 (Windows and Linux), NFR-33 (evidence), NFR-34 (run ID in logs), NFR-35.

## 5. Self-Healing Engine

**Purpose.** Repair broken locators during execution without hiding real defects, reducing script maintenance, which is one of the central problems this project addresses.

**Inputs.**
- Failure context: error type, failing step, the stored `Locator` record, DOM snapshot, screenshot reference (from the Execution Engine through the `LocatorHealer` interface).
- Healing configuration: attempt limits, confidence threshold, whether the LLM step is enabled.

**Outputs.**
- A healed element handle for the running step, or "not healable" / "not healed".
- `HealingEvent` records: old and new locator, strategy used, confidence score, validation result, outcome, approval flag (initially *proposed*).
- Healing metrics: attempts, success rate per strategy and per mutation type.

**Methodology (cost-ordered ladder).**
1. *Classify:* decide whether the failure is a locator failure or an application defect (for example, an assertion failure or an element that exists but shows the wrong value); defects are returned unchanged.
2. *Fallback strategies:* try the stored fallback locators in order.
3. *DOM-similarity matching:* score candidate elements on tag, attributes, visible text, position in the tree and neighbouring elements; take the best candidate above the threshold.
4. *LLM suggestion* (last resort): send the masked, size-limited DOM fragment and the original intent through the LLM Gateway; accept only schema-valid candidates.
5. *Validate:* re-run the step and check that the element's role, text and context match the original; reject a "present but wrong" element.
6. *Record:* write every attempt as a `HealingEvent`; the result is flagged "healed" and shown in reports.
7. *Approve (Gate 2):* a permanent update to the locator repository requires explicit human approval; without it the change applies to the current run only.
8. *Bound the effort:* stop at the per-step and per-run attempt limits.

**Dependencies.** Execution Engine (calls it through `LocatorHealer`); Script Generator's locator repository; LLM Gateway and Data Masking and Validation Layer (step 4); SQLite Persistence; Audit Logging. External: none directly. Consumed by: Failure Analyzer (healing history), Reporting Engine (healing metrics). The evaluation harness (FR-38) exercises it with seeded mutations.

**Related FRs.** FR-22 (detect locator failure), FR-23 (repair in cost order), FR-24 (validate healed locator), FR-25 (persist events, approval before permanent change), FR-26 (attempt limits and success rate); supporting FR-30 (masking before the LLM step), FR-38 (mutation harness), FR-39 (healing metric).

**Related NFRs.** NFR-03 (≤ 3 s fallback repair, ≤ 30 s LLM repair), NFR-06 (graceful LLM failure), NFR-08, NFR-13 (injection through DOM content), NFR-18 (≥ 90% test coverage of this logic), NFR-31 (human approval), NFR-35.

## 6. Failure Analyzer

**Purpose.** Shorten defect investigation by classifying each failed test, explaining the likely cause and suggesting the next step, while marking the output as advisory.

**Inputs.**
- Failed `TestResult` records, logs and stack traces, artefact references (screenshot, DOM snapshot), healing history for the same test (from persistence).

**Outputs.**
- `FailureAnalysis` records: category (locator issue, assertion or application defect, timing or flaky, environment or infrastructure, test data, unknown), root-cause explanation, evidence references, suggested remediation, confidence (0–1), cluster ID, label "AI-generated advisory".
- Classification accuracy figures when run against the hand-labelled evaluation set.

**Methodology.**
1. *Deterministic pre-classification:* rules on exception type, timeout and connection signatures, and healing history settle clear cases without an LLM call.
2. *Clustering:* group failures by a normalised signature (exception type, message pattern, step) so duplicates are analysed once.
3. *LLM reasoning for ambiguous cases:* build a compact context from logs, trace, DOM snippet and screenshot reference (the image itself is not sent); redact and mask; request a schema-bound answer through the LLM Gateway.
4. *Confidence and validation:* assign a score (rule certainty or model-reported confidence combined with rule agreement); reject invalid output; low-confidence results are labelled "unknown".
5. *Persist and audit.*
6. *Evaluate:* compare predictions with the hand-labelled set to compute accuracy (Unit 6 metric).

**Dependencies.** Execution Engine and Self-Healing Engine outputs (via persistence); Data Masking and Validation Layer; LLM Gateway; SQLite Persistence; Audit Logging. Consumed by: Reporting Engine. It can run standalone on any PyTest output (NFR-21).

**Related FRs.** FR-27 (failure categories), FR-28 (root cause and remediation), FR-29 (clusters and confidence), FR-30 (redaction); supporting FR-36, FR-37, FR-39 (classification accuracy).

**Related NFRs.** NFR-10 (output validation), NFR-13, NFR-15, NFR-18 (≥ 90% test coverage of classification logic), NFR-21 (standalone use), NFR-30 (labelled output), NFR-35.

## 7. Reporting Engine

**Purpose.** Turn stored run data into reports and metrics that engineers and non-technical stakeholders can read, and provide the evidence base for Chapter 4 and the Unit 6 evaluation.

**Inputs.**
- All run data from persistence: requirements, test cases, results, artefacts, healing events, failure analyses, audit summaries.
- Report configuration: formats, template set, run selection.

**Outputs.**
- Per-run HTML report (summary first, then per-test detail, screenshots, healing events, failure analysis), Markdown report, PDF report, all from one report data model.
- Metrics JSON and CSV: pass rate, healing success rate, classification accuracy, requirement coverage ratio, script executability rate, generation latency, API cost per run, code coverage.
- `Report` records (path, format, run ID).

**Methodology.**
1. *Assemble a single report model* from repository queries (no format-specific logic in the data layer).
2. *Render* through templates: HTML (self-contained, opens offline), Markdown, PDF (export of the HTML or Markdown; deferrable, ADR-018).
3. *Compute metrics* from stored data with Pandas; derive cost from token usage in audit records; coverage ratio from requirement-to-test-case links; executability from validation and first-run results.
4. *Traceability links:* each result links to its screenshot, log, test case and requirement.
5. *Accessibility:* summary-first layout, sufficient contrast, text alternatives for screenshots.
6. *Export* metrics as CSV for Appendix B.

**Dependencies.** SQLite Persistence; evidence store; all upstream modules' records; Audit Logging (cost). External: template and PDF tooling (to be chosen in Unit 5). Consumed by: Dashboard and the user.

**Related FRs.** FR-31 (HTML report), FR-32 (Markdown and PDF), FR-39 (Unit 6 metrics); supporting FR-26 (healing rate shown), FR-34 (trace links).

**Related NFRs.** NFR-01 (render within 5 s), NFR-08 (identical output for identical data), NFR-29 (readability and accessibility), NFR-33 (evidence), NFR-35.

## 8. Dashboard

**Purpose.** Present metrics and trends across runs in one view for the live demonstration (the most heavily weighted presentation item) and the published portfolio, without needing a server.

**Inputs.**
- Metrics JSON/CSV and run history (from the Reporting Engine and persistence), read-only.

**Outputs.**
- A static HTML dashboard: pass rate, healing success rate, classification accuracy, requirement coverage ratio, script executability rate, code coverage, API cost per run, generation latency, and trends across runs; links to run reports and evidence.

**Methodology.**
1. *Aggregate* run history with Pandas (per run, per module, per mutation type).
2. *Pre-render* charts and tables into static HTML with embedded data, so it works offline and on GitHub Pages and exposes no write path.
3. *Trace:* every figure links to the stored data or report it came from.
4. *Degrade gracefully:* with fewer than three runs, show the available values and say that no trend exists yet.
5. *Review* for readability by non-technical readers (summary first).

**Dependencies.** Reporting Engine outputs; SQLite Persistence (read-only); Pandas. No LLM use, no network access. Consumed by: the user, the presentation and the portfolio.

**Related FRs.** FR-33 (dashboard metrics and trend); supporting FR-39 (metrics source), FR-34 (traceability links).

**Related NFRs.** NFR-01 (render within 5 s), NFR-26 (platform independence), NFR-29 (readability and accessibility), NFR-33 (evidence).

## 9. Module Dependency Matrix

Rows depend on columns. **I** = interface call, **P** = via persistence, **G** = via LLM Gateway, **S** = uses cross-cutting service.

| Module ↓ depends on → | RA | TG | SG | EE | SH | FA | RE | Masking | Gateway | Persistence | Audit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Requirement Analyzer | | | | | | | | S | G | S | S |
| Test Case Generator | P | | | | | | | S | G | S | S |
| Script Generator | | P | | | | | | S | G | S | S |
| Execution Engine | | | P | | I | | | | | S | S |
| Self-Healing Engine | | | P | I | | | | S | G | S | S |
| Failure Analyzer | | | | P | P | | | S | G | S | S |
| Reporting Engine | P | P | P | P | P | P | | | | S | S |
| Dashboard | | | | | | | P | | | S (read-only) | |

No cycles exist except the intended Execution Engine ⇄ Self-Healing Engine call, which runs through the `LocatorHealer` interface owned by `core`.

## 10. Requirement Coverage by Module

| Module | FRs | NFRs |
|---|---|---|
| Requirement Analyzer | 01–05 | 02, 08, 10, 13, 15, 22, 30, 35 |
| Test Case Generator | 06–11 | 02, 08, 15, 22, 30–32, 35 |
| Script Generator | 12–16 | 11, 17, 21, 22, 30 |
| Execution Engine | 17–21 | 04, 07, 08, 11, 23, 26, 33–35 |
| Self-Healing Engine | 22–26 | 03, 06, 08, 13, 18, 31, 35 |
| Failure Analyzer | 27–30 | 10, 13, 15, 18, 21, 30, 35 |
| Reporting Engine | 31, 32, 39 | 01, 08, 29, 33, 35 |
| Dashboard | 33 | 01, 26, 29, 33 |
| Cross-cutting and Orchestrator | 34–38 (FR-38 shared with Self-Healing) | 05, 06, 07, 09, 12, 14, 16, 19, 20, 24, 25, 27, 28 |

Every FR (01–39) and NFR (01–35) appears in at least one row.

## 11. Open Items

1. Library choices (validation, templating, PDF, charts) are deferred to Unit 5 and will be recorded as ADRs.
2. Confidence-score method for the Failure Analyzer (§6 step 4) is to be fixed at Unit 5 and validated in Unit 6.
3. Keep this file and `04_COMPONENT_ARCHITECTURE.md` §3 consistent, or retire `04` §3 once you approve this file.
