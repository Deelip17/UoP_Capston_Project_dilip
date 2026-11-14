# Non-Functional Requirements (NFR-01 to NFR-35)

**Version:** 1.0 · **Date:** 14 Nov 2026 · **Authoritative copy** (supersedes `architecture/03_NON_FUNCTIONAL_REQUIREMENTS.md`, which now points here)
**Feeds:** Unit 3 AA Q1c · Report §3.3 (NFRs as 3.3.x), §3.2 (security and ethics as 3.2.x) · **Related:** `FUNCTIONAL_REQUIREMENTS.md`, `architecture/07_SECURITY_ETHICS_CONTROLS.md`
**Basis:** approved architecture (ADR-002), scope (ADR-001), accepted NFR interpretations (ADR-007), control vocabulary (ADR-015), risk register R1–R17 (ADR-014).

*AI-generated draft: review before submission. Numeric targets are **initial design targets, not measured results**; they are recalibrated after the Unit 5 pilot and every change is logged in `PROJECT_DECISIONS.md` (ADR-017). GDPR and other regulatory interpretation is outside this document: requirements here are engineering controls only, and wording must be confirmed by the Data Privacy Officer or Legal.*

## 1. Executive Summary

35 measurable NFRs cover the categories Unit 3 AA names (performance, usability, reliability, scalability, security) plus maintainability, privacy, ethical AI and evidence/metrics. They replace the eight qualitative legacy NFRs (mapping in §5). Two legacy statements were re-scoped under ADR-007 because a literal reading cannot be met or measured: "response time < 5 s" (LLM calls routinely take longer) and "95% availability" (there is no hosted service). Every NFR has a rationale, a related module and an acceptance criterion that names its verification method.

**Verification methods:** **T** automated test · **A** analysis or inspection · **D** demonstration with screenshot evidence · **M** measurement in the Unit 6 evaluation.
**Module codes:** as in `FUNCTIONAL_REQUIREMENTS.md`, plus **ALL** (every module) and **CI** (GitHub Actions pipeline).
**Control status (ADR-015):** every security-related NFR is a *target for the prototype*; controls such as AES-256, MFA, SSO and RBAC are **Designed-only** and are not NFRs of the prototype.

## 2. Requirements by Category

### 2.1 Performance

| ID | Description | Rationale | Module | Acceptance Criteria |
|---|---|---|---|---|
| NFR-01 | Non-LLM operations (configuration load, database query, report rendering, CLI start-up) shall respond within 5 seconds. | Preserves the legacy 5 s response-time goal where it is achievable (ADR-007); LLM calls are budgeted separately in NFR-02/03. | ALL (excluding LLM calls) | p95 ≤ 5 s over 30 repetitions on a 4-core, 8 GB machine. Verified by T, M. |
| NFR-02 | Requirement analysis and test-case generation shall complete within a bounded time. | LLM latency dominates; a budget keeps the live demo within its 10–15 minute slot (roadmap R10). | RA, TG | ≤ 60 s per requirement and ≤ 10 min for a 20-requirement batch, reported as generation latency. Verified by M. |
| NFR-03 | Self-healing shall add bounded overhead per healed step. | Healing must not make tests slower than the maintenance it saves. | SH | Fallback-locator repair ≤ 3 s; LLM-assisted repair ≤ 30 s (median of the mutation catalogue run). Verified by M. |
| NFR-04 | Framework overhead on test execution shall be small. | The framework should not distort execution results or CI minutes. | EE | Wall-clock time ≤ 110% of the same suite run with plain PyTest. Verified by M. |

### 2.2 Reliability and Availability

| ID | Description | Rationale | Module | Acceptance Criteria |
|---|---|---|---|---|
| NFR-05 | Scheduled CI runs and clean-environment CLI runs shall succeed. | Re-scoped "95% availability" (ADR-007): a CLI prototype is not a hosted service, so reliability is the success rate of runs. | CI, Orchestrator | ≥ 95% of runs succeed over the evaluation window, excluding sample-application outages. Verified by M. |
| NFR-06 | The system shall degrade gracefully when the OpenAI API fails: retry with back-off, then use the mock or cached provider (FR-36). | API outages are a stated risk (R4) and must not break a demo (R10). | LLM Gateway | Fault-injection tests (timeout, 429, 5xx, invalid JSON) produce zero unhandled exceptions. Verified by T. |
| NFR-07 | Run state shall be durable: an interrupted run shall be resumable or reported as incomplete. | Prevents corrupt evidence and unreliable metrics. | SQLite Persistence, Orchestrator | After a forced process kill the database passes an integrity check and the run is marked incomplete. Verified by T. |
| NFR-08 | Execution shall be repeatable. | Reproducible evaluation is required for credible Unit 6 results (R9). | ALL | With the mock LLM and fixed seeds, two runs produce identical generated artefacts and results. Verified by T. |

### 2.3 Security (OWASP Top 10, least privilege, secure API storage)

| ID | Description | Rationale | Module | Acceptance Criteria |
|---|---|---|---|---|
| NFR-09 | API keys shall be loaded only from the environment or a secret store and shall never appear in code, logs, reports, the database or LLM prompts. | Secure API key storage is an approved principle and risk R16 (key exposure). | LLM Gateway, CI | Secret scan of the repository is clean; a grep test of logs, reports and the database finds no key pattern. Verified by T, A. |
| NFR-10 | All external input (requirements, configuration, URLs) shall be validated, and LLM output shall be treated as untrusted and checked against a schema before use. | OWASP input validation; LLM output can be malformed or malicious. | Data Masking and Validation Layer | 100% of LLM outputs in tests pass through schema validation; invalid output is rejected. Verified by T. |
| NFR-11 | Generated scripts shall run with least privilege: static checks (FR-15), allow-listed hosts (FR-21), no shell access, no writes outside the working and evidence directories. | Generated code is untrusted (R17). | SG, EE | All forbidden-construct fixtures are rejected; an attempted write outside the permitted directories fails. Verified by T. |
| NFR-12 | Dependencies shall be pinned and scanned, and high or critical vulnerabilities shall block merging. | OWASP vulnerable-components risk; supply-chain hygiene (depends on ADR-010 decision for pip-audit). | CI | Zero open high or critical findings on `main`. Verified by T (CI). |
| NFR-13 | The system shall resist prompt injection in requirement text and DOM content sent to the LLM (delimiting, instruction hierarchy, output validation). | Untrusted content shares the prompt with instructions (R15). | LLM Gateway | An injection fixture set does not change pipeline behaviour or leak data. Verified by T. |
| NFR-14 | Security-relevant events and LLM calls shall be logged for auditability, with log injection prevented. | Auditability is an approved principle; supports incident review. | Audit Logging | An audit record exists for each LLM call (FR-37); newline and control characters in input cannot forge log entries. Verified by T. |

### 2.4 Privacy and Compliance

| ID | Description | Rationale | Module | Acceptance Criteria |
|---|---|---|---|---|
| NFR-15 | Only synthetic or public data shall be used in inputs, test data and evidence, and redaction shall precede every LLM call (FR-30). | Data minimisation and organisational confidentiality (ADR-005; risk R14 data egress). | Data Masking and Validation Layer | Redaction tests pass; a repository scan finds no client names or data. Verified by T, A. |
| NFR-16 | Run artefacts and the database shall be stored locally and deletable by a single documented command. | Gives the user control over retention (privacy guidance; confirm wording with the Data Privacy Officer). | SQLite Persistence | The purge command removes all run data and is covered by a test. Verified by T. |

### 2.5 Maintainability and Reusability

| ID | Description | Rationale | Module | Acceptance Criteria |
|---|---|---|---|---|
| NFR-17 | Components shall depend on `core` interfaces, not on one another's internals. | Modularity is a project rule and the basis of maintainability (legacy NFR4). | ALL | An automated import-rule check reports zero forbidden imports in CI. Verified by T. |
| NFR-18 | Unit-test coverage shall meet defined thresholds. | Unit testing is required in Unit 5 and by the project rule "all code includes unit tests". | ALL | ≥ 80% line coverage overall; ≥ 90% for self-healing and failure-classification logic. Verified by T. |
| NFR-19 | Linting, formatting and type checks shall pass. | Keeps the code reviewable by a solo developer without peer review. | ALL, CI | Linter and formatter report zero errors; type check is clean on `core`. Verified by T. |
| NFR-20 | Every component package shall have a README and public docstrings, and each architectural change an ADR. | Project rule "include documentation"; supports Unit 7 documentation. | ALL | 100% of component packages have a README; ADR log up to date at each unit gate. Verified by A. |
| NFR-21 | Components shall be usable standalone through their public API. | Legacy NFR8 (reusable codebase); makes components demonstrable and testable in isolation. | ALL | Each component has a runnable standalone example (for instance, the Failure Analyzer on any PyTest output). Verified by D. |
| NFR-22 | Prompts and schemas shall be versioned and changes recorded in the changelog. | Prompts are a primary quality lever and must be reviewable and reproducible. | LLM Gateway | The prompt version is stored on every audit record; a prompt change without a changelog entry fails review. Verified by A. |

### 2.6 Scalability and Portability

| ID | Description | Rationale | Module | Acceptance Criteria |
|---|---|---|---|---|
| NFR-23 | Test execution shall scale with parallel workers. | Scalability is named in Unit 3 AA and legacy NFR5. | EE | Speed-up ≥ 2.5× with 4 workers on the sample suite. Verified by M. |
| NFR-24 | The storage layer shall sit behind a repository interface so SQLite can be replaced without changing components. | Keeps the prototype's SQLite choice from limiting a future production design. | SQLite Persistence | Component tests pass using an in-memory fake repository. Verified by T. |
| NFR-25 | The LLM provider shall sit behind an interface so providers and models are swappable. | Avoids vendor lock-in and enables the mock provider (FR-36). | LLM Gateway | The mock and OpenAI providers pass the same contract tests. Verified by T. |
| NFR-26 | The system shall run on Windows and Linux with Python 3.12. | The development machine is Windows and CI runs on Linux; Python 3.12 is the approved version (ADR-000). | ALL, CI | The CI matrix (ubuntu and windows) is green; macOS is best-effort. Verified by T. |

### 2.7 Usability

| ID | Description | Rationale | Module | Acceptance Criteria |
|---|---|---|---|---|
| NFR-27 | A new user shall be able to install and run the sample pipeline from the README. | "Usable interface" (legacy NFR7) is delivered as CLI plus HTML report, not a GUI (ADR-007; avoids scope creep, R3). | Orchestrator | A first-time run completes in ≤ 15 minutes with ≤ 5 commands, shown in a recorded walkthrough. Verified by D. |
| NFR-28 | CLI errors shall be actionable (what failed, why, what to do). | Reduces support effort and supports the demo. | Orchestrator | A review of all error messages finds each states cause and remedy. Verified by A. |
| NFR-29 | Reports shall be readable by non-technical stakeholders: summary first, drill-down second, accessible contrast, text alternatives for screenshots. | Stakeholders include non-technical QA managers (Unit 2 stakeholder analysis); accessibility is good practice. | RE, DB | A review checklist is passed for the sample report and dashboard. Verified by A, D. |

### 2.8 Ethical and Responsible AI

| ID | Description | Rationale | Module | Acceptance Criteria |
|---|---|---|---|---|
| NFR-30 | Every AI-generated artefact shall be labelled as such with model and prompt version. | Transparency is an approved ethical principle; prevents confusion with human-written tests. | ALL | 100% of generated artefacts in tests carry a label, model and prompt version. Verified by T. |
| NFR-31 | AI output affecting test scope or permanent locator changes shall require explicit human approval (FR-10, FR-25). | Human validation principle; main mitigation of poor AI output (R5). | TG, SH | No unapproved permanent change is possible in negative tests. Verified by T. |
| NFR-32 | Generated scenarios shall be reviewed for coverage across the user roles and locales named in the requirements, and limitations reported honestly. | Algorithmic fairness principle; avoids systematically missing minority use cases. | TG | The review is recorded in the Unit 6 evaluation with any gaps listed. Verified by A. |

### 2.9 Evidence, Metrics and Observability

| ID | Description | Rationale | Module | Acceptance Criteria |
|---|---|---|---|---|
| NFR-33 | Every run shall produce academic evidence (screenshots, logs, JUnit and coverage output) stored under `evidence/` and registered. | The project rule requires screenshots and evidence for submission (risk R7: evidence gaps). | EE, CI | The evidence register (E01–E20) is complete at each unit gate. Verified by D. |
| NFR-34 | Logging shall be structured and carry a run identifier across all components. | Enables traceability (FR-34) and debugging of multi-stage runs. | ALL | The run identifier is present on 100% of log lines in a full pipeline test. Verified by T. |
| NFR-35 | Metrics hooks (timers, counters, token and cost logging) shall exist in the core from Unit 5. | Unit 6 results depend on data that must already be collected during Unit 5 (roadmap critical path). | ALL | Each component emits latency and outcome counters in a pipeline test. Verified by T. |

## 3. Decisions Already Taken (ADR-007)

| NFR | Legacy wording | Interpretation adopted |
|---|---|---|
| NFR-01 | Response time < 5 s | Applies to non-LLM operations; LLM latency reported separately (NFR-02, NFR-03). Note `MASTER_PLAN.md` §9.5 lists "NFR1 < 5 s" as a generation-latency metric; report generation latency against NFR-02 instead. |
| NFR-05 | 95% availability | Success rate of CI and clean-environment runs |
| NFR-27 | Usable interface | CLI plus HTML report; no GUI |

## 4. How NFRs Influence the Design (Unit 3 AA requirement)

| NFR group | Design decision it drives |
|---|---|
| Reliability (NFR-06, 08) | Provider interface with mock and cache fallback; fixed seeds and temperature |
| Security (NFR-09–14) | Single LLM Gateway (mask, validate, audit); static script validator; host allow-list |
| Privacy (NFR-15, 16) | Redaction before every LLM call; local-only storage with purge command |
| Maintainability (NFR-17–22) | Component packages over a shared kernel; import rules; versioned prompts |
| Scalability (NFR-23–26) | Stateless components; repository and provider ports; parallel workers; CI matrix |
| Ethics (NFR-30–32) | Review states in the data model; approval gate before permanent healing |
| Evidence and metrics (NFR-33–35) | Run identifier and artefact convention; metrics hooks in `core/metrics` |

## 5. Traceability to Legacy Requirements

| Legacy | Legacy text | New |
|---|---|---|
| NFR1 | Response time less than 5 seconds | NFR-01, 02, 03, 04 |
| NFR2 | 95% system availability | NFR-05, 06, 07 |
| NFR3 | Secure API key storage | NFR-09 (with NFR-10 to 14) |
| NFR4 | Maintainable architecture | NFR-17 to 20, 22 |
| NFR5 | Scalable design | NFR-23, 24, 25 |
| NFR6 | Reliable execution | NFR-06, 07, 08 |
| NFR7 | Usable interface | NFR-27, 28, 29 |
| NFR8 | Reusable codebase | NFR-21, 25 |

## 6. Alignment With Unit 3 Assignment

Unit 3 AA Q1c asks for NFRs "such as performance, usability, reliability, scalability, and security that influence your design decisions": performance §2.1, reliability §2.2, security §2.3, scalability §2.6, usability §2.7, with the design influence shown in §4. Word limit for Q1+Q2 is 750–1,250 words, so submit a condensed table grouped by category and cite this file for the full catalogue.

## 7. Open Items

1. Calibrate numeric targets after the Unit 5 pilot and log changes (ADR-017).
2. ADR-010 decision needed for pip-audit and secret scanning (NFR-09, NFR-12 rely on them).
3. Data Privacy Officer or Legal to confirm privacy wording (NFR-15, NFR-16).
