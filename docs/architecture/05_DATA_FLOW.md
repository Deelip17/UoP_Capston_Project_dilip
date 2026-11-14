# 05 — Data Flow

**Version:** 1.0 · **Date:** 14 Nov 2026 · **Feeds:** Unit 3 AA Q1a ("system components and their interactions"), Report §3.3 Data Flow and System Components, §3.4 Design Diagrams (DFD) · **Design only, no code**
**Sources:** `01_SYSTEM_ARCHITECTURE.md` (components, interactions A1–A17, gates), `02_COMPONENT_ARCHITECTURE.md` (module inputs and outputs), `SYSTEM_REQUIREMENTS/` (FR/NFR), `07_SECURITY_ETHICS_CONTROLS.md` (trust boundaries B1–B4).
**Companion:** `06_SEQUENCE_FLOW.md` covers module communication, error handling and time-ordered behaviour.

*AI-generated draft: review before submission.*

## 1. Executive Summary

Data moves through the framework as **versioned, schema-validated records** stored in SQLite Persistence (structured data) and an evidence store (files). Every record carries the run ID and the IDs of the records it came from, which gives the end-to-end traceability required by FR-34. The only point where project data leaves the machine is the LLM Gateway, which masks before sending, validates what returns and writes an audit record; four trust boundaries (B1–B4) are marked on the diagrams. This file covers the **requirement flow** (§5), the **data flow** (§2–4, 6), the **reporting flow** (§7) and the data lifecycle (§8); module communication and error handling are in `06`.

## 2. Level 0 — Context Diagram

```mermaid
flowchart LR
  QA(["Tester / QA Engineer"]) -- "requirements, configuration, approvals" --> SYS["AI-Powered Test Automation Framework"]
  SYS -- "reports, dashboard, evidence" --> QA
  SYS <-- "masked prompts / validated responses" --> OAI(["OpenAI API"])
  SYS -- "browser actions on allow-listed URLs" --> SUT(["System Under Test<br/>public demo web app"])
  SUT -- "DOM, page responses" --> SYS
  CI(["GitHub Actions"]) -- "trigger, mock-LLM mode by default" --> SYS
  SYS -- "artefacts, results" --> CI
```

## 3. Level 1 — Data Flow Diagram

Processes follow the canonical modules; stores D1–D7 are logical groups of SQLite tables or files.

```mermaid
flowchart TB
  IN["Requirement text<br/>txt, md, user stories"] -->|B1| P1
  subgraph PIPE["Pipeline"]
    P1["P1 Requirement Analyzer"]
    P2["P2 Test Case Generator"]
    P3["P3 Script Generator"]
    P4["P4 Execution Engine"]
    P5["P5 Self-Healing Engine"]
    P6["P6 Failure Analyzer"]
    P7["P7 Reporting Engine"]
    P8["P8 Dashboard"]
  end
  P1 -->|AnalyzedRequirement| D1[("D1 Requirements")]
  D1 --> P2
  P2 -->|"TestCase Pending, TestData"| D2[("D2 Test cases")]
  D2 --> G1{"Gate 1<br/>human approval"}
  G1 -->|Approved| P3
  G1 -->|"Rejected or Pending"| D2
  P3 -->|"Script, Locator"| D3[("D3 Scripts and locators")]
  D3 --> P4
  P4 -->|"locator failure context"| P5
  P5 -->|"healed element or not healed"| P4
  P5 -->|"HealingEvent proposed"| D4[("D4 Healing history")]
  P4 -->|"Run, TestResult"| D5[("D5 Results and logs")]
  P4 -->|"screenshots, DOM, JUnit"| D6[("D6 Evidence store")]
  D5 --> P6
  D4 --> P6
  D6 --> P6
  P6 -->|FailureAnalysis| D7[("D7 Analyses")]
  D5 --> P7
  D4 --> P7
  D7 --> P7
  D6 --> P7
  P7 -->|"HTML, MD, PDF"| OUT["Reports"]
  P7 -->|"metrics JSON, CSV"| P8
  P8 --> DASH["Static dashboard"]
  D4 --> G2{"Gate 2<br/>approve permanent locator change"}
  G2 -->|approved| D3
  P4 -->|"browser actions B3"| SUT(["System Under Test"])
  OUT -->|B4| READER(["Reader"])
```

Every process also writes events to Audit Logging, and every process that calls a model does so through the LLM Gateway (§6).

## 4. Data Dictionary

| Record | Produced by | Consumed by | Key fields | Store |
|---|---|---|---|---|
| `AnalyzedRequirement` | Requirement Analyzer | Test Case Generator, Reporting | req_id, source_ref, content_hash, actors, actions, preconditions, outcomes, risk, risk_rationale, ambiguity_flags, prompt_version, ai_label | D1 |
| `TestScenario` | Test Case Generator | Test Case Generator | scenario_id, req_id, type (positive, negative, boundary) | D2 |
| `TestCase` | Test Case Generator | Script Generator, Reporting | tc_id, scenario_id, req_id, steps, expected, priority, review_status, ai_label | D2 |
| `TestData` | Test Case Generator | Script Generator, Execution Engine | tc_id, dataset (synthetic) | D2 |
| `Script` | Script Generator | Execution Engine | script_id, tc_id, framework, path, validation_result | D3 |
| `Locator` | Script Generator, approved healing | Execution Engine, Self-Healing | loc_id, page, name, primary, fallbacks, version | D3 |
| `Run` | Orchestrator | all | run_id, started, status, config_hash, driver, environment, git_sha | D5 |
| `TestResult` | Execution Engine | Failure Analyzer, Reporting | result_id, run_id, tc_id, status, duration, error, retries, healed_flag, log_ref | D5 |
| `Artifact` | Execution Engine | Failure Analyzer, Reporting | result_id, type (screenshot, trace, dom, log, junit), path, sha256 | D6 + index in D5 |
| `HealingEvent` | Self-Healing Engine | Failure Analyzer, Reporting, review | result_id, loc_id, old, new, strategy, confidence, validated, approved, outcome | D4 |
| `FailureAnalysis` | Failure Analyzer | Reporting | result_id, category, cause, remediation, confidence, cluster_id, ai_label | D7 |
| `LlmAudit` | LLM Gateway | Reporting (cost, latency) | call_id, run_id, component, model, prompt_version, tokens_in, tokens_out, input_hash, status | audit table |
| `Report` | Reporting Engine | user, Dashboard | run_id, format, path, generated_at | files + index |

## 5. Requirement Flow (traceability and lifecycle)

A requirement is the unit that everything else is traced to (FR-34). Its identity is fixed at ingestion and carried through every later record.

### 5.1 Lineage

```mermaid
flowchart LR
  R["Requirement<br/>source text"] -->|"ID assigned (FR-04)"| AR["AnalyzedRequirement<br/>req_id"]
  AR --> SC["TestScenario<br/>req_id"]
  SC --> TC["TestCase<br/>tc_id, req_id"]
  TC --> SCR["Script<br/>script_id, tc_id"]
  SCR --> TR["TestResult<br/>result_id, tc_id"]
  TR --> HE["HealingEvent<br/>result_id"]
  TR --> FA["FailureAnalysis<br/>result_id"]
  TR --> RP["Report row<br/>req_id to result"]
```

The reverse query (result → requirement) and the forward query (requirement → all results) must both be answerable from one database query (FR-34 acceptance criterion).

### 5.2 Requirement states

```mermaid
stateDiagram-v2
  [*] --> Received
  Received --> Rejected: "validation or masking fails (B1)"
  Received --> Analysed: "schema-valid extraction"
  Analysed --> Flagged: "ambiguous or untestable (FR-05)"
  Flagged --> Analysed: "clarified by user"
  Analysed --> Covered: "at least one Approved test case (Gate 1)"
  Covered --> Executed: "scripts run"
  Executed --> Passed: "all linked tests pass"
  Executed --> FailedAnalysed: "failure analysed (FR-27)"
  Passed --> [*]
  FailedAnalysed --> [*]
  Rejected --> [*]
```

"Covered" drives the requirement coverage ratio (FR-39): requirements with at least one Approved test case divided by eligible requirements (those not Flagged or Rejected).

## 6. LLM Data Path and Trust Boundaries

```mermaid
flowchart LR
  C["Component"] --> M["1 Masking and validation<br/>(secrets, PII, injection screen)"]
  M --> T["2 Versioned prompt template"]
  T --> P["3 Provider call<br/>(timeout, retry, back-off)"]
  P -->|"B2 network"| OAI(["OpenAI API"])
  OAI --> V["4 Schema validation<br/>(output is untrusted)"]
  P -. "API down or disabled" .-> MK["Mock / cache provider"] --> V
  V --> A["5 Audit record<br/>(hash, tokens, prompt version)"]
  A --> C
```

| Data class | Leaves the machine? | Control |
|---|---|---|
| Requirement text (public or synthetic only) | Yes, after masking | FR-02, FR-30; NFR-15 |
| Trimmed DOM fragment, error text | Yes, after masking and size cap | FR-30; NFR-13 |
| API keys, credentials, personal data | **No** | Masking, environment-only secrets (NFR-09) |
| Screenshots | **No** (referenced by path only) | Not transmitted in the prototype |
| Audit record | No (local table) | Hash of input, no raw prompt or secret (FR-37) |

Trust boundaries: **B1** user or file → Requirement Analyzer; **B2** LLM Gateway → OpenAI; **B3** Execution Engine → system under test; **B4** Reporting Engine → reader (controls in `07` §2).

## 7. Reporting Flow

```mermaid
flowchart TB
  subgraph SRC["Sources (SQLite and evidence store)"]
    R1["Requirements and test cases"]
    R2["Results and artefacts"]
    R3["Healing events"]
    R4["Failure analyses"]
    R5["LLM audit (tokens, latency)"]
    R6["Coverage output"]
  end
  SRC --> Q["Repository queries"]
  Q --> RM["Report data model<br/>(single source for all formats)"]
  RM --> H["HTML renderer<br/>self-contained"]
  RM --> MD["Markdown renderer"]
  H --> PDF["PDF export<br/>(deferrable, ADR-018)"]
  RM --> MET["Metric computation<br/>(Pandas)"]
  MET --> CSV["metrics.csv (Appendix B)"]
  MET --> JSON["metrics.json"]
  JSON --> DB["Dashboard<br/>static HTML"]
  H --> OUT["reports/ folder"]
  MD --> OUT
  PDF --> OUT
  DB --> OUT
  OUT -->|"B4: review before sharing"| READER(["Reader or portfolio"])
```

### 7.1 Report content (HTML report, FR-31)

| Section (summary first, NFR-29) | Source records |
|---|---|
| Run summary: pass, fail, healed, skipped; duration; driver | `Run`, `TestResult` |
| Requirement coverage table | `AnalyzedRequirement`, `TestCase` |
| Per-test detail with screenshot and log links | `TestResult`, `Artifact` |
| Healing events with confidence and approval state | `HealingEvent` |
| Failure analysis by category and cluster | `FailureAnalysis` |
| Metrics and cost | `LlmAudit`, computed metrics |
| Provenance: model, prompt versions, mock or live, commit | `Run`, `LlmAudit` |

### 7.2 Metric derivation (FR-33, FR-39; proposed definitions, fixed at Unit 5)

| Metric | Definition | Source |
|---|---|---|
| Pass rate | Passed ÷ executed (healed passes counted separately) | `TestResult` |
| Healing success rate | Validated healed events ÷ healing attempts, per strategy and mutation type | `HealingEvent`, mutation catalogue (FR-38) |
| Classification accuracy | Correct categories ÷ labelled failures in the hand-labelled set | `FailureAnalysis`, labelled set |
| Requirement coverage ratio | Requirements with ≥ 1 Approved case ÷ eligible requirements | `AnalyzedRequirement`, `TestCase` |
| Script executability rate | Scripts that pass static validation and run to the first assertion without framework error ÷ scripts generated | `Script`, `TestResult` |
| Generation latency | Median seconds per requirement for analysis plus generation | `LlmAudit`, stage timers |
| API cost per run | Tokens × configured price per token | `LlmAudit` |
| Code coverage | Line coverage from the coverage tool for the framework's own code | CI output |

All reports state whether the LLM was live or mock-generated, so mock results are never mistaken for model results (FR-36).

## 8. Data Lifecycle

| Stage | Data | Retention | Disposal |
|---|---|---|---|
| In run | Records, artefacts | Until the run ends | — |
| After run | Database and evidence store | Local; curated samples committed for the portfolio | Purge command (NFR-16) |
| CI | Uploaded artefacts | Set explicitly (proposed: 14 days for runs, 90 days for release evidence) | Automatic expiry |
| Audit | `LlmAudit` | With the database | With the database |

## 9. Alignment With Unit 3 Assignment

Q1a asks for "system components and their interactions": §3 (components and flows), §4 (what is exchanged) and `06` (how and when). The FR/NFR connection is shown by requirement IDs in the diagrams and the tables.

## 10. Open Items

1. Confirm CI artefact retention values (§8).
2. Metric definitions (§7.2) are proposals to be fixed at Unit 5 and recalibrated under ADR-017 if they change.
3. Whether screenshots may ever go to a vision-capable model (currently excluded for privacy and cost).
