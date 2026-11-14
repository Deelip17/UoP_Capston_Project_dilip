# 01 — System Architecture

**Version:** 1.0 · **Date:** 14 Nov 2026 · **Feeds:** Unit 3 AA Q1 (a, b), Report §3.1 System Architecture, §3.3, §3.4 · **Design only, no code**
**Sources:** `SYSTEM_REQUIREMENTS/FUNCTIONAL_REQUIREMENTS.md` (FR-01–39), `NON_FUNCTIONAL_REQUIREMENTS.md` (NFR-01–35), `knowledge/MASTER_PLAN.md` §2 (canonical names), ADR-001, 002, 006, 015.
**Related, not repeated here:** per-component method detail `04_COMPONENT_ARCHITECTURE.md` §3 · trust boundaries and controls `07_SECURITY_ETHICS_CONTROLS.md` · data model and flows `05_DATA_FLOW.md`, `06_SEQUENCE_FLOW.md` · repository layout `01_REPOSITORY_STRUCTURE.md` (shares the 01 prefix; no content overlap).

*AI-generated draft: review before submission.*

## 1. Architecture Overview

**Purpose.** An AI-powered, supervised pipeline that turns natural-language requirements into executed, self-repairing, analysed and reported automated tests (ADR-001: working prototype, public demo apps only).

**Style.** A **pipeline of eight components** coordinated by a Pipeline Orchestrator, supported by **four cross-cutting services**. Components exchange validated, versioned records through SQLite Persistence rather than calling each other's internals (NFR-17). The only exception is the Execution Engine ⇄ Self-Healing Engine loop, which runs synchronously during a test through an interface owned by `core`.

**Canonical modules (MASTER_PLAN §2, ADR-002).**

| # | Component | Short role |
|---|---|---|
| 1 | Requirement Analyzer | Requirements → structured, risk-rated records |
| 2 | Test Case Generator | Records → reviewed, traceable test cases and data |
| 3 | Script Generator | Approved cases → Playwright/Selenium PyTest scripts |
| 4 | Execution Engine | Runs scripts, captures evidence |
| 5 | Self-Healing Engine | Repairs broken locators during execution |
| 6 | Failure Analyzer | Classifies and explains failures |
| 7 | Reporting Engine | Builds reports and metrics |
| 8 | Dashboard | Shows run history and metrics |
| X1 | Data Masking and Validation Layer | Cross-cutting: masks sensitive data, validates input and model output |
| X2 | SQLite Persistence | Cross-cutting: single store behind a repository interface |
| X3 | Audit Logging | Cross-cutting: append-only record of decisions and LLM calls |
| X4 | LLM Gateway | Cross-cutting: the only path to the OpenAI API (ADR-006) |
| — | Pipeline Orchestrator and CLI | Sequencing, review gates, run identifier (FR-34, FR-35) |

**Architectural drivers** (requirements that most shaped the design):

| Driver | Requirements | Resulting decision |
|---|---|---|
| Untrusted input and output around an LLM | FR-02, FR-15, FR-30; NFR-09, 10, 13 | One LLM Gateway; masking before, schema validation after |
| Human oversight of AI | FR-10, FR-25; NFR-30, 31 | Approval gates after test-case generation and before permanent locator change |
| Reproducible, measurable evaluation | FR-36, FR-38, FR-39; NFR-08, 35 | Mock/cache provider; seeded mutation harness; metrics hooks in the core |
| Maintainability by one developer | NFR-17–22, 24, 25 | Shared kernel, ports for storage and LLM, import rules |
| Two automation tools | FR-12, 13, 17 | Driver adapter with one script model |
| Evidence for submission | FR-18, 31; NFR-33 | Screenshots and registered artefacts on every run |

## 2. Component Responsibilities

Security duties per component are in `07` §3; this table states functional responsibility, boundaries and key requirements.

| Component | Responsible for | Explicitly not responsible for | Inputs | Outputs | FR / NFR |
|---|---|---|---|---|---|
| **Requirement Analyzer** | Intake in three formats; sanitising; LLM extraction of actors, actions, preconditions, outcomes, ambiguities; stable IDs; risk rating; ambiguity flags | Writing tests; deciding what is approved | Requirement text or file | `AnalyzedRequirement` records | FR-01–05; NFR-10 |
| **Test Case Generator** | Scenarios (positive, negative, boundary); test cases with traceability; synthetic data; de-duplication; review status; export | Producing code; running anything | `AnalyzedRequirement` | `TestCase`, `TestData`, exports | FR-06–11; NFR-30–32 |
| **Script Generator** | Compiling approved cases to PyTest scripts via page objects and a locator repository; primary and fallback locators; static validation of generated code | Executing scripts; repairing locators at run time | Approved `TestCase`; optional DOM snapshot | Scripts, `Locator` records | FR-12–16; NFR-11 |
| **Execution Engine** | Running scripts on Playwright or Selenium; allow-list check; screenshots; logs; retries; parallel workers; calling the healing interface | Deciding if a failure is a defect; interpreting causes | Scripts, run configuration | `Run`, `TestResult`, artefacts | FR-17–21; NFR-04, 23 |
| **Self-Healing Engine** | Distinguishing locator failure from defect; cost-ordered repair (fallbacks, DOM similarity, LLM suggestion); validation of the healed element; recording every event; attempt limits | Permanently changing the locator repository without approval | Failure context, DOM snapshot, `Locator` | Healed element handle, `HealingEvent` (proposed) | FR-22–26; NFR-03, 31 |
| **Failure Analyzer** | Failure categories; root-cause explanation and remediation; clustering; confidence | Fixing the application under test | Failed `TestResult`, logs, artefact references, healing history | `FailureAnalysis` | FR-27–30 |
| **Reporting Engine** | Per-run HTML, Markdown and PDF reports; metric computation for the Dashboard | Collecting results (that is the Execution Engine's job) | Run data from persistence | Reports, metrics JSON/CSV | FR-31, 32, 39; NFR-29 |
| **Dashboard** | Static visual summary of metrics and trends; links to reports and evidence | Writing data (read-only) | Metrics, run history | Static HTML dashboard | FR-33; NFR-29 |
| **Data Masking and Validation Layer** | Masking secrets and personal data; input and output validation; static checks | Business decisions | Any text bound for the LLM or storage | Masked, validated text | FR-02, 15, 30; NFR-10, 15 |
| **SQLite Persistence** | Storing all records behind a repository interface; run identifiers; traceability queries | Business logic | Records from all components | Queryable store | FR-19, 34; NFR-07, 24 |
| **Audit Logging** | One audit record per LLM call; structured, run-correlated logs | Storing secrets or raw prompts | Events | Append-only log | FR-37; NFR-14, 34 |
| **LLM Gateway** | Versioned prompt templates; provider call with retry and back-off; schema validation; mock/cache fallback; token and cost metrics | Deciding what to ask | Masked request | Validated typed result | FR-36, 37; NFR-06, 22, 25 |
| **Pipeline Orchestrator and CLI** | Stage sequencing; review gates; run identifier; configuration; resume or mark incomplete | Component internals | CLI commands, configuration file | Pipeline runs | FR-34, 35; NFR-07, 27, 28 |

## 3. Component Interactions

### 3.1 Interaction matrix

Mechanism **P** = through SQLite Persistence (asynchronous hand-over of a stored record); **I** = synchronous call through a `core` interface; **G** = through the LLM Gateway.

| # | From → To | What is exchanged | Mech. | Trigger / gate | Req. |
|---|---|---|---|---|---|
| A1 | User → CLI/Orchestrator | Requirement file, configuration, review decisions | I | Command | FR-01, 35 |
| A2 | Orchestrator → Requirement Analyzer | Requirement text, run ID | I | Stage start | FR-01 |
| A3 | Requirement Analyzer → Masking Layer | Raw requirement text | I | Before any LLM call | FR-02, 30 |
| A4 | Requirement Analyzer, Test Case Generator, Script Generator, Self-Healing Engine, Failure Analyzer → LLM Gateway | Masked request and schema | G | Per LLM task | NFR-10, 13 |
| A5 | LLM Gateway → OpenAI API (or mock/cache) | Masked prompt, response | external | Retry, then fallback | FR-36 |
| A6 | Requirement Analyzer → Persistence → Test Case Generator | `AnalyzedRequirement` | P | Stage complete | FR-03, 04 |
| A7 | Test Case Generator → Persistence → (review) → Script Generator | `TestCase` with status Pending, then Approved | P | **Gate 1:** human approval | FR-10 |
| A8 | Script Generator → Persistence → Execution Engine | Scripts, `Locator` records | P | Static validation passed | FR-15, 17 |
| A9 | Execution Engine → system under test | Browser actions on allow-listed URLs | external | Test step | FR-21 |
| A10 | Execution Engine ⇄ Self-Healing Engine | Failure context, DOM snapshot ↔ healed element or "not healed" | I | Locator failure only | FR-22–24 |
| A11 | Self-Healing Engine → Persistence | `HealingEvent` (proposed) | P | Each attempt | FR-25 |
| A12 | Persistence → Script Generator/locator repository | Permanent locator update | P | **Gate 2:** human approval | FR-25 |
| A13 | Execution Engine → Persistence and evidence store | `TestResult`, screenshots, logs | P | Test end | FR-18, 19 |
| A14 | Persistence → Failure Analyzer → Persistence | Failed results → `FailureAnalysis` | P | Run end | FR-27–29 |
| A15 | Persistence → Reporting Engine → reports and metrics | All run data | P | Run end | FR-31, 32, 39 |
| A16 | Reporting Engine/Persistence → Dashboard | Metrics, history | P | On demand | FR-33 |
| A17 | All components → Audit Logging | Events, LLM call records | I | Continuous | FR-37; NFR-34 |

### 3.2 Control flow (summary)

1. The Orchestrator creates a `Run` and starts the stages in order. Each stage reads its input from persistence and writes its output back, so a stage can be re-run alone (FR-35) and an interrupted run can be resumed or marked incomplete (NFR-07).
2. Two **human gates** stop the pipeline: approval of generated test cases (Gate 1, when review mode is on) and approval of permanent locator changes (Gate 2). Healing within a run is temporary and flagged "healed".
3. The only tight loop is Execution Engine ⇄ Self-Healing Engine during a single test step; it is bounded by attempt limits (FR-26) and time budgets (NFR-03).
4. Failure analysis and reporting run after execution, so a slow or unavailable LLM cannot block test execution.

### 3.3 Dependency rules

Components import `core` and the public models of upstream components only (NFR-17). Only the LLM Gateway uses the OpenAI SDK; only SQLite Persistence uses the database driver. The Execution Engine uses a `LocatorHealer` interface defined in `core`, so there is no circular dependency with the Self-Healing Engine. These rules are enforced by an automated import check in CI.

## 4. Architecture Narrative

*(Prose for Report §3.1; adjust citations to verified register entries before use.)*

The framework is organised as a pipeline in which each stage transforms one kind of artefact into the next while keeping a link back to the original requirement. A tester supplies requirements through a command-line interface. The Requirement Analyzer validates and masks the text, asks a language model to extract the actors, actions, preconditions and expected outcomes, assigns each requirement a stable identifier and a risk rating, and flags statements that are too vague to test. The Test Case Generator turns each structured requirement into positive, negative and boundary scenarios and then into detailed test cases with synthetic data. These cases are held until a human reviewer approves them, which keeps responsibility for test scope with the engineer rather than the model.

The Script Generator compiles approved cases into PyTest scripts for Playwright or Selenium. Instead of asking the model for free-form code, it fills structured slots in templates and stores locators in a repository, each with a primary strategy and ordered fallbacks. Every generated script is statically checked for forbidden calls and secrets before it is saved. The Execution Engine then runs the scripts against an allow-listed application, capturing screenshots, logs and timings in every run.

When a step fails because an element cannot be found, the Execution Engine hands the context to the Self-Healing Engine. The engine first checks that the failure is a locator problem rather than an application defect, then tries stored fallbacks, then similarity matching against the page, and only then asks the language model for a candidate. A repair is accepted only if the element's role and text match the original, and it is recorded as a proposal that changes the locator repository permanently only after approval. After execution, the Failure Analyzer classifies each remaining failure, explains its likely cause and groups duplicates. The Reporting Engine assembles reports and metrics from the stored data, and the Dashboard presents them as a static page that works offline and can be published with the portfolio.

Four cross-cutting services keep this safe and measurable. All model calls pass through a single gateway that applies masking, uses versioned prompts, validates the response against a schema, falls back to a mock or cached provider when the API is unavailable, and writes an audit record. SQLite Persistence stores every artefact behind an interface, which provides traceability from requirement to report and allows the database to be replaced later. Audit Logging records decisions without storing secrets. The resulting design favours simplicity and supervision over autonomy: it is a prototype evaluated on public demonstration applications, and controls such as encryption at rest, multi-factor authentication and role-based access are documented as designed but not implemented.

## 5. Architecture Diagram Specification

Use this to draw **Figure 1** in draw.io (or equivalent). The existing `architecture/image.png` and `dataflow_fig.png` should be checked against this specification for naming and layering before reuse.

### 5.1 Format

A4 landscape; Times New Roman or Arial 10–12 pt (readable when the image is 6.5 inches wide in the report); export PNG at 300 dpi and keep the `.drawio` source in `architecture/diagrams/`; use colour-blind-safe fills **and** different line styles so it remains readable in greyscale. Caption (APA 7): **Figure 1** (bold), then the title in italic title case on the next line: *System Architecture of the AI-Powered Test Automation Framework*. Provide alt text: "Layered architecture with eight pipeline components, four cross-cutting services and external systems."

### 5.2 Layers (top to bottom, full-width bands with a label at the left)

| Layer | Contents (exact labels) |
|---|---|
| L1 Actors | "Tester / QA Engineer"; "GitHub Actions (CI)" |
| L2 Interface and orchestration | "Command-Line Interface"; "Pipeline Orchestrator" |
| L3 Pipeline components (left to right, numbered) | "1 Requirement Analyzer" → "2 Test Case Generator" → "3 Script Generator" → "4 Execution Engine" ⇄ "5 Self-Healing Engine"; below 4: "6 Failure Analyzer" → "7 Reporting Engine" → "8 Dashboard" |
| L4 Cross-cutting services | "Data Masking and Validation Layer"; "LLM Gateway"; "SQLite Persistence"; "Audit Logging" |
| L5 External systems and stores | "OpenAI API"; "System Under Test (public demo web app)"; "SQLite database file"; "Evidence store (screenshots, logs)"; "GitHub repository" |

### 5.3 Connectors

| Connector | Style | Label |
|---|---|---|
| Actor → CLI | solid | "requirements, configuration, approvals" (A1) |
| CLI → Orchestrator → each component | thin grey solid | "run ID, stage start" (A2) |
| 1 → 2 → 3 → 4 | thick solid, left to right | "AnalyzedRequirement", "TestCase (approved)", "Scripts + Locators" (A6–A8) |
| 4 ⇄ 5 | thick double-headed | "failure context ↔ healed element" (A10) |
| 4 → 6 → 7 → 8 | thick solid | "TestResult", "FailureAnalysis", "metrics" (A13–A16) |
| Components 1, 2, 3, 5, 6 → LLM Gateway | dashed | "masked requests" (A4); route through the Masking Layer |
| LLM Gateway → OpenAI API | dashed with "mock/cache fallback" note | A5 |
| 4 → System Under Test | solid | "browser actions, allow-listed URLs" (A9) |
| All components → SQLite Persistence | thin solid, drawn as a bus under L3 | "records" |
| Persistence → SQLite file; 4 → Evidence store | solid | — |
| All → Audit Logging | thin dotted bus | "events" (A17) |

### 5.4 Overlays and markers

- **Gate markers:** two diamond icons labelled "Gate 1: approve test cases" (between 2 and 3) and "Gate 2: approve permanent locator change" (between 5 and the locator repository).
- **Trust boundaries (07 §2):** four dashed red rectangles or lines labelled B1 (input), B2 (OpenAI), B3 (system under test), B4 (output).
- **Control-status badge** (ADR-015) only on items that are Designed-only in text; the diagram itself shows implemented elements only.

### 5.5 Legend and checklist

Legend: pipeline flow (thick), service call (dashed), data bus (thin), human gate (diamond), trust boundary (dashed red), cross-cutting service (grey fill), pipeline component (blue fill), external system (white with double border).
Checklist before export: all 13 names match the canonical list exactly; no retired names (Data Management Layer, AI Analysis Engine, Test Case Generation Module, "Test Generator"); arrows A1–A17 present; both gates shown; every box readable at 6.5 inches wide; caption and alt text added.

## 6. Technology Mapping

Status: **Approved** (ADR-000; tooling ADR-025), **Standard** (ships with an approved tool or the Python standard library), **Proposed** (needs a decision, ADR-010), **Open** (to decide at the start of Unit 5).

| Component / concern | Technology | Status | Notes |
|---|---|---|---|
| All components | Python 3.12 | Approved | Packages per component (`01_REPOSITORY_STRUCTURE.md`) |
| Requirement Analyzer, Test Case Generator, Script Generator, Self-Healing (LLM step), Failure Analyzer | OpenAI API via the official Python SDK, called only from the LLM Gateway | Approved | Model and budget: open input O-4 |
| LLM Gateway | Versioned prompt files; JSON-schema validation; mock/cache provider | Standard / Open | Validation library choice at Unit 5 (for example pydantic or jsonschema) |
| Data Masking and Validation Layer | Python standard library (regular expressions, `ast` for script checks) | Standard | No external dependency needed for the prototype |
| Script Generator | Template-based generation; Playwright and Selenium adapters | Approved | Adapter pattern; templates keep model output in safe slots |
| Execution Engine | PyTest; Playwright (Python); Selenium WebDriver; JUnit XML output | Approved | Parallel workers via a PyTest plugin (pytest-xdist, **Approved**, ADR-025) |
| Self-Healing Engine | DOM parsing and similarity scoring in Python; LLM step via gateway | Standard | No machine-learning training (ADR-001) |
| Failure Analyzer | Rule-based pre-classifier plus LLM for ambiguous cases | Approved / Standard | |
| SQLite Persistence | SQLite via the Python standard-library driver, repository interface | Approved | Parameterised queries; replaceable (NFR-24) |
| Audit Logging | Python `logging` with structured (JSON) formatter and run ID | Standard | Append-only file plus audit table |
| Reporting Engine | HTML and Markdown from templates; PDF export | Approved formats; **Open** tool | Template engine (for example Jinja2) and PDF library to decide in Unit 5; PDF is deferrable (ADR-018) |
| Dashboard | Pandas aggregation; pre-rendered static HTML with charts | Approved (Pandas); Open (chart library) | Static so it runs offline and on GitHub Pages |
| Metrics and evaluation | Pandas; CSV export; seeded mutation harness | Approved | FR-38, 39 |
| Pipeline Orchestrator and CLI | Python standard-library `argparse` (or equivalent) with a configuration file | Standard / Open | |
| Version control | Git, GitHub | Approved | `project-management/GIT_STRATEGY.md` |
| CI/CD | GitHub Actions | Approved | `08_CICD_DESIGN.md` |
| Security scanning | pip-audit; GitHub built-in secret scanning and push protection (CodeQL and gitleaks rejected) | **Approved** (ADR-025) | NFR-09, 12 |
| Packaging and deployment | Docker | **Approved, conditional** (ADR-025: Dockerfile only, Unit 6, if Docker Desktop is available) | Unit 6 Part C |
| Code quality | Linter, formatter, type checker, import-rule checker | Open | NFR-17, 19 |

**Decisions (Technology):** ADR-010 is resolved by ADR-025 (accepted: pip-audit, pytest-xdist, GitHub secret scanning, Docker conditional; rejected: CodeQL, gitleaks, Allure); Unit 5 choices for validation, templating, PDF and chart libraries, to be recorded as new ADRs when made.

## 7. Requirement Coverage Check

| Requirement group | Covered by |
|---|---|
| FR-01–05 | Requirement Analyzer, Masking Layer (§2, A2–A6) |
| FR-06–11 | Test Case Generator, Gate 1 (A7) |
| FR-12–16 | Script Generator (A8) |
| FR-17–21 | Execution Engine (A9, A13) |
| FR-22–26 | Self-Healing Engine, Gate 2 (A10–A12) |
| FR-27–30 | Failure Analyzer, Masking Layer (A14) |
| FR-31–33, 38, 39 | Reporting Engine, Dashboard, evaluation support (A15, A16) |
| FR-34–37 | Orchestrator, Persistence, Gateway, Audit Logging (A1, A2, A4, A5, A17) |
| NFR-01–35 | Drivers in §1; technology in §6; verification in the NFR file |

## 8. Open Items

1. Make the Unit 5 library choices (§6); ADR-010 is resolved by ADR-025.
2. Check `architecture/image.png` and `dataflow_fig.png` against §5 and either reuse or redraw.
3. `04_COMPONENT_ARCHITECTURE.md` §2 diagram and §3 text overlap partly with this file; keep §3 there for method detail, and treat this file as the overview used for Q1 and Report §3.1.
