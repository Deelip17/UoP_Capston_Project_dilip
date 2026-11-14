# Functional Requirements (FR-01 to FR-39)

**Version:** 1.0 · **Date:** 14 Nov 2026 · **Authoritative copy** (supersedes `architecture/02_FUNCTIONAL_REQUIREMENTS.md`, which now points here)
**Feeds:** Unit 3 AA Q1c · Report §3.3 (FRs as 3.3.x) · **Related:** `architecture/04_COMPONENT_ARCHITECTURE.md`, `NON_FUNCTIONAL_REQUIREMENTS.md`
**Basis:** approved architecture (ADR-002: Requirement Analyzer, Test Case Generator, Script Generator, Execution Engine, Self-Healing Engine, Failure Analyzer, Reporting Engine, Dashboard; cross-cutting Data Masking and Validation Layer, SQLite Persistence, Audit Logging, LLM Gateway), scope (ADR-001: prototype, public demo apps only) and Unit 3 AA Q1c ("what the system should do").

*AI-generated draft: review before submission. Requirement wording follows the "unambiguous, verifiable" guidance in the Unit 3 reading (Letaw, 2024, Ch. 3); confirm the section reference against the reading.*

## 1. Executive Summary

39 testable functional requirements cover the full pipeline from requirement intake to dashboard. They preserve all ten legacy requirements (FR1–FR10, mapping in §5) and add what the legacy set omitted: **self-healing** (a core approved component), human approval gates, security controls on LLM use and generated code, traceability, and the evaluation support that Unit 6 depends on. Each requirement states its rationale, owning module and acceptance criterion so it can be tested in Units 5–7 and traced in the report.

**Priority (MoSCoW):** **M** Must (needed for the prototype demo) · **S** Should · **C** Could. 26 M, 12 S, 1 C. If Units 5–6 run short (roadmap risk R3), defer in this order: Dashboard polish → PDF export (FR-32) → Selenium parity (FR-13, FR-17 Selenium part), per ADR-018.

**Module codes:** RA Requirement Analyzer · TG Test Case Generator · SG Script Generator · EE Execution Engine · SH Self-Healing Engine · FA Failure Analyzer · RE Reporting Engine · DB Dashboard · EV Evaluation support (cross-cutting) · X Cross-cutting (Orchestrator, LLM Gateway, Persistence).

## 2. Requirements by Module

### 2.1 Requirement Analyzer (RA)

| ID | Description | Rationale | Module | Acceptance Criteria | Pri |
|---|---|---|---|---|---|
| FR-01 | The system shall accept requirements as plain text, Markdown or user-story format, supplied as a file path (CLI) or as text (API call). | Enterprise requirements arrive in mixed formats; a single entry point is the start of the pipeline and of traceability. | RA | A sample file in each of the three formats is ingested without error; an unsupported format returns an actionable error naming the supported formats. | M |
| FR-02 | The system shall validate and sanitise all requirement input (size limit, encoding, control characters, prompt-injection screening) before any LLM call. | Requirement text is untrusted input that reaches an LLM (OWASP input validation; risk R15 prompt injection). | RA, Data Masking and Validation Layer | Oversized, mis-encoded and injection-pattern fixtures are rejected or neutralised, and each event is written to the audit log. | M |
| FR-03 | The system shall extract structured items from each requirement using an LLM: actors, actions, preconditions, expected outcomes and ambiguities. | Structured extraction is what makes automated test generation possible and checkable. | RA | For every fixture the output validates against the `AnalyzedRequirement` schema; schema violations are rejected, not passed on. | M |
| FR-04 | The system shall assign each requirement a stable identifier and a risk rating (High, Medium, Low) with a one-sentence rationale. | Supports risk-based testing (approved methodology) and prioritisation of generated tests. | RA | Every analysed requirement carries an ID, a rating and a rationale; re-running on unchanged input yields the same IDs. | S |
| FR-05 | The system shall flag ambiguous or untestable requirements for human clarification instead of silently generating tests from them. | Poor input produces poor tests (risk R5); surfacing ambiguity is cheaper than debugging bad tests. | RA | Fixtures with vague or contradictory wording are flagged with a stated reason; flagged items are excluded from generation until resolved. | S |

### 2.2 Test Case Generator (TG)

| ID | Description | Rationale | Module | Acceptance Criteria | Pri |
|---|---|---|---|---|---|
| FR-06 | The system shall generate test scenarios (positive, negative and boundary) for each analysed requirement. | Directly addresses the manual test-design effort in the problem statement and applies recognised test-design techniques. | TG | Each eligible fixture requirement receives at least one scenario of each type. | M |
| FR-07 | The system shall expand each scenario into a test case with ID, title, preconditions, steps, expected results, priority and the originating requirement ID. | Complete, linked test cases are the input to script generation and the basis for traceability. | TG | All fields are present and schema-valid for every generated case. | M |
| FR-08 | The system shall generate synthetic test data for each test case and shall not use real personal data. | Privacy by design; only synthetic or public data may be used (ADR-005; GDPR guidance to be confirmed by the Data Privacy Officer). | TG | A pattern test finds no real PII in generated data; format constraints in the requirement are honoured. | S |
| FR-09 | The system shall detect and remove duplicate or near-duplicate test cases. | LLMs repeat themselves; duplicates inflate suite size and execution time. | TG | Seeded duplicates in a fixture are collapsed and the number removed is reported. | C |
| FR-10 | The system shall record a human review status (Pending, Approved, Rejected) for each generated test case and, when review mode is enabled, forward only Approved cases to script generation. | Human validation is an approved ethical principle and the main mitigation for poor AI output (R5). | TG, Orchestrator | In review mode no Pending or Rejected case is ever scripted (negative test); status changes are logged. | M |
| FR-11 | The system shall export test cases as JSON, CSV and Markdown and re-import them. | Allows offline review, evidence for the report, and reuse outside the framework. | TG | The three export files are produced and re-imported with no data loss. | S |

### 2.3 Script Generator (SG)

| ID | Description | Rationale | Module | Acceptance Criteria | Pri |
|---|---|---|---|---|---|
| FR-12 | The system shall generate executable Playwright (Python) test scripts from approved test cases. | Playwright is an approved automation tool; executable output is the framework's core value. | SG | A generated script passes a syntax check and executes against the sample application. | M |
| FR-13 | The system shall generate executable Selenium (Python) test scripts from approved test cases. | Selenium is an approved tool and enables the Playwright/Selenium comparison in Chapter 2 and 4. | SG | As FR-12, for Selenium. | M |
| FR-14 | The system shall generate scripts in PyTest format using a page-object and locator-repository pattern, so locators are held in one place per page. | Centralised locators are what make automated repair (FR-23) and maintenance possible. | SG | Locators of each page reside in exactly one repository file; scripts reference locators by name only. | M |
| FR-15 | The system shall statically validate every generated script (syntax, forbidden imports and calls, no hard-coded secrets) before it is saved or run. | Generated code is untrusted and executes on the user's machine (risk R17, OWASP injection). | SG, Data Masking and Validation Layer | Fixtures containing `os.system`, `eval`, network or file-system calls outside the allowed set, or embedded secrets are rejected with a reason. | M |
| FR-16 | The system shall record, for each locator, a primary strategy and ordered fallback strategies (id, CSS, XPath, text/role, attributes). | Provides the first, cheapest rung of the self-healing ladder. | SG | Each locator record holds at least two strategies wherever the page offers them. | S |

### 2.4 Execution Engine (EE)

| ID | Description | Rationale | Module | Acceptance Criteria | Pri |
|---|---|---|---|---|---|
| FR-17 | The system shall execute generated tests through PyTest on Playwright and on Selenium, selectable by configuration. | Meets the "automated execution" objective on both approved tools. | EE | The same suite runs on both drivers against the sample application and returns comparable results. | M |
| FR-18 | The system shall capture a screenshot on every test failure and at configurable checkpoints, and optionally trace or video (Playwright). | Screenshots are mandatory academic evidence and the input to failure analysis. | EE | A screenshot file exists for each failure and is linked to its result record. | M |
| FR-19 | The system shall store logs, durations, status and environment information for every run and test in SQLite. | Persistence enables trend metrics, traceability and post-run analysis. | EE, SQLite Persistence | After the process exits, the run and its results can be queried and match the console output. | M |
| FR-20 | The system shall support headless execution, configurable timeouts, retries and parallel workers. | Needed for CI, for stability against flaky tests and for scalability (NFR-23). | EE | Each setting is honoured in a test run; retry counts per test are recorded. | S |
| FR-21 | The system shall execute tests only against an allow-listed set of base URLs. | Prevents the framework being pointed at client or unintended systems (ADR-005; least privilege; R17). | EE | A run targeting a non-listed URL aborts before any browser action and logs the reason. | M |

### 2.5 Self-Healing Engine (SH)

| ID | Description | Rationale | Module | Acceptance Criteria | Pri |
|---|---|---|---|---|---|
| FR-22 | The system shall detect a locator failure (element not found, stale or not interactable) and distinguish it from an application defect. | Healing a genuine defect would hide a regression; correct classification is the precondition for safe repair. | SH | An injected locator change is classified as a locator failure; an injected assertion failure is not. | M |
| FR-23 | The system shall attempt repair in cost order: stored fallback locators, then DOM-similarity matching, then an LLM-suggested locator. | Cheapest-first reduces latency, cost and data sent to the LLM (R4, R14). | SH, LLM Gateway | The repair path and outcome are recorded for every attempt; the LLM step is reached only after the first two fail. | M |
| FR-24 | The system shall validate a healed locator by re-running the step and checking that the element's role, text and context match the original before accepting it. | Guards against false passes where a wrong element is found. | SH | In a negative fixture, a present but wrong element is rejected and the step still fails. | M |
| FR-25 | The system shall persist every healing event (old and new locator, strategy, confidence, outcome), flag it as *proposed*, and update the locator repository permanently only after human approval. | Human validation and auditability; prevents silent drift of the test suite. | SH, SQLite Persistence | The healing history table is populated; attempting a permanent update without approval fails. | M |
| FR-26 | The system shall limit healing attempts per step and per run and report the healing success rate. | Bounds time and API cost; provides the healing metric for Unit 6. | SH, RE | Limits are configurable and enforced; the rate appears in the run report. | S |

### 2.6 Failure Analyzer (FA)

| ID | Description | Rationale | Module | Acceptance Criteria | Pri |
|---|---|---|---|---|---|
| FR-27 | The system shall classify each failed test as locator issue, assertion/application defect, timing/flaky, environment/infrastructure, test data, or unknown. | Slow defect investigation is a stated problem; categories let engineers triage quickly. | FA | On a hand-labelled fixture set every failure receives a category; accuracy is computed for Unit 6. | M |
| FR-28 | The system shall produce a root-cause explanation and a suggested remediation for each failure from logs, stack trace, screenshot reference and DOM snippet. | Delivers the AI-assisted analysis objective and shortens triage time. | FA, LLM Gateway | Each output contains a cause, references to the evidence used, and a next step. | M |
| FR-29 | The system shall group similar failures into clusters and give each classification a confidence score. | Reduces duplicate investigation; confidence tells reviewers where to look first. | FA | Failures with the same signature share a cluster ID; every classification has a score between 0 and 1. | S |
| FR-30 | The system shall redact secrets and personal data from all artefacts before they are sent to an LLM. | Data minimisation and protection of credentials (R14, R16; GDPR guidance to be confirmed). | Data Masking and Validation Layer | A redaction test with seeded secrets and personal data shows none reaching the provider (checked on the audit hash and a captured payload). | M |

### 2.7 Reporting Engine (RE) and Dashboard (DB)

| ID | Description | Rationale | Module | Acceptance Criteria | Pri |
|---|---|---|---|---|---|
| FR-31 | The system shall generate an HTML report for each run with summary, per-test results, screenshots, healing events and failure analysis. | Lack of intelligent reporting is a stated problem; the HTML report is primary evidence for Chapter 4. | RE | The report opens offline without a server and links every screenshot and log it refers to. | M |
| FR-32 | The system shall generate Markdown and PDF versions of the report from the same data model. | Approved report formats (ADR-000); Markdown for the repository, PDF for submission. | RE | Both files are produced from one data model and show identical figures. | S |
| FR-33 | The Dashboard shall present pass rate, healing success rate, classification accuracy, requirement coverage ratio, script executability rate, code coverage, API cost per run, generation latency and run trend. | Supports the evaluation (Unit 6), the live demo (15 rubric points) and the portfolio. | DB | A trend across at least three stored runs is displayed; each metric can be traced to stored data. | S |

### 2.8 Evaluation Support (EV)

| ID | Description | Rationale | Module | Acceptance Criteria | Pri |
|---|---|---|---|---|---|
| FR-38 | The system shall provide a seeded locator-mutation harness that alters the sample application (id, class, XPath and text changes) from a committed catalogue. | Self-healing must be evaluated reproducibly, not anecdotally (risk R9). | EV, SH | The same seed produces the same mutations; the healing success rate is computed per mutation type. | M |
| FR-39 | The system shall compute the Unit 6 metrics from stored data: requirement coverage ratio, script executability rate, healing success rate, classification accuracy against a hand-labelled set, generation latency and API cost per run. | Unit 6 requires at least two quantitative metrics with a results table and chart (roadmap M12). | EV, RE | Metrics are exported as CSV for Appendix B; at least two quantitative metrics are available for Unit 6. | M |

### 2.9 Cross-cutting (X)

| ID | Description | Rationale | Module | Acceptance Criteria | Pri |
|---|---|---|---|---|---|
| FR-34 | The system shall maintain end-to-end traceability: requirement → test case → script → execution → failure → report. | Traceability is a core QA principle and a Unit 3 theme (version control and traceability). | X, SQLite Persistence | A single query returns the full chain for any test result, and the reverse. | M |
| FR-35 | The system shall provide a command-line interface to run the whole pipeline or any single stage, driven by a configuration file. | Enables stage-wise testing, CI use and the demo; the CLI is the prototype's user interface. | Orchestrator | `run`, per-stage commands and `--help` exist and are documented; invalid configuration is rejected with a clear message. | M |
| FR-36 | The system shall fall back to a deterministic mock or cached LLM provider when the OpenAI API is unavailable or disabled. | Mitigates API outage and cost (R4), supports reproducible CI and demo reliability (R10). | LLM Gateway | With the API disabled, the pipeline completes on the fixture set and marks outputs as mock-generated. | S |
| FR-37 | The system shall write an audit record for every LLM call (component, prompt version, model, token usage, input hash) without storing secrets. | Auditability (approved security principle) and the source of cost metrics. | LLM Gateway, Audit Logging | Exactly one audit record exists per LLM call; a scan of the audit table finds no secrets or raw prompts. | S |

## 3. Out of Scope (ADR-001)

Mobile-native, desktop, API and performance testing; model training or fine-tuning; production or multi-tenant deployment; use of client systems or data; automatic correction of application defects; authentication, RBAC, SSO and encryption at rest (status **Designed-only** under ADR-015, not claimed as implemented).

## 4. Module Summary

| Module | IDs | Count | Must |
|---|---|---|---|
| Requirement Analyzer | FR-01–05 | 5 | 3 |
| Test Case Generator | FR-06–11 | 6 | 3 |
| Script Generator | FR-12–16 | 5 | 4 |
| Execution Engine | FR-17–21 | 5 | 4 |
| Self-Healing Engine | FR-22–26 | 5 | 4 |
| Failure Analyzer | FR-27–30 | 4 | 3 |
| Reporting Engine | FR-31–32 | 2 | 1 |
| Dashboard | FR-33 | 1 | 0 |
| Evaluation support | FR-38–39 | 2 | 2 |
| Cross-cutting | FR-34–37 | 4 | 2 |
| **Total** | | **39** | **26** |

## 5. Traceability to Legacy Requirements

| Legacy | Legacy text | New |
|---|---|---|
| FR1 | System shall accept requirement input | FR-01, FR-02 |
| FR2 | …generate test scenarios | FR-06 |
| FR3 | …generate test cases | FR-07, FR-08 |
| FR4 | …generate Playwright scripts | FR-12, FR-14 |
| FR5 | …generate Selenium scripts | FR-13, FR-14 |
| FR6 | …execute automated tests | FR-17 |
| FR7 | …capture screenshots | FR-18 |
| FR8 | …store execution logs | FR-19 |
| FR9 | …analyze failures | FR-27, FR-28 |
| FR10 | …generate reports | FR-31, FR-32 |
| *(catalogue "Self healing")* | not in FR1–FR10 | FR-22 to FR-26 |

## 6. Alignment With Unit 3 Assignment

| Unit 3 AA requirement | Where met |
|---|---|
| Q1c: FRs describing what the system should do | §2 |
| FRs and NFRs "that influence your design decisions" | Each FR names its module; NFR influence table in `NON_FUNCTIONAL_REQUIREMENTS.md` §4 |
| Module-wise input, output, methodology | `architecture/04_COMPONENT_ARCHITECTURE.md` §3 (cites FR IDs) |
| Word limit Q1+Q2: 750–1,250 | Submit a condensed table (legacy FR1–FR10 plus self-healing, grouped by module); cite this file for the full catalogue |

## 7. Open Items

1. Confirm that deferred items (§1) are acceptable after the Unit 5 pilot (ADR-017 recalibration log).
2. Verify the Letaw (2024) citation and chapter reference against the course reading.
