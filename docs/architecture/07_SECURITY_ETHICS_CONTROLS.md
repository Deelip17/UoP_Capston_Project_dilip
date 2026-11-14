# 07 SECURITY, ETHICS AND CONTROLS

Version 1.0 · 14 Nov 2026 · Fills the unused number 07. Source for Unit 3 DF replacement text and Chapter 3.2/3.3/5.3. Component names follow ADR-002; control labels follow `GLOSSARY.md` §3 (Implemented, Designed-only, Inherited, Out of scope). FR/NFR IDs refer to the requirement catalogue in `architecture/02–03`.

## 1. Architecture description (prose, reusable in Ch3.3)
The framework is a pipeline of eight components coordinated by a Pipeline Orchestrator and exposed through a command-line interface. The Requirement Analyzer receives requirements as text and returns structured requirement records. The Test Case Generator turns each record into test cases with steps, data and expected results, and a human reviewer approves them. The Script Generator converts approved test cases into Playwright or Selenium PyTest scripts. The Execution Engine runs the scripts and collects results and artefacts; when a locator fails, the Self-Healing Engine proposes a replacement with a confidence score. The Failure Analyzer classifies each failed result, the Reporting Engine builds reports and metrics, and the Dashboard shows run history. Three cross-cutting services support every step: the Data Masking and Validation Layer, SQLite Persistence and Audit Logging. All calls to the OpenAI API pass through one LLM Gateway.

## 2. Data flow description (prose, reusable in Ch3.4)
Data enters as requirement text from a file or the command line (trust boundary 1: untrusted input). The Data Masking and Validation Layer replaces sensitive values with placeholders and validates the input format. The LLM Gateway then fills a versioned prompt template, sends only the masked text across the network to the OpenAI API (trust boundary 2: external service), receives a response, and validates it against a schema before it is used; both the request summary and the response are written to the audit log. Validated test cases and scripts are stored in SQLite. The Execution Engine runs approved scripts against a public demo web application (trust boundary 3: system under test) and stores results, screenshots and logs. Healing events, failure classifications and metrics are written to SQLite, and the Reporting Engine reads from SQLite to produce reports (trust boundary 4: output to the reader). Human approval gates sit after test case generation and before any permanent locator change.

### Trust boundaries
| # | Boundary | Data crossing | Main threat | Controls |
|---|---|---|---|---|
| 1 | User / file → Requirement Analyzer | Requirement text | Sensitive data; prompt injection | Input validation, masking |
| 2 | LLM Gateway → OpenAI API | Masked prompts and responses | Data egress; key exposure; malicious output | Masking, secret handling, schema validation |
| 3 | Execution Engine → system under test | Browser actions | Executing unsafe generated code | Approval gate, static check, isolation, public apps only |
| 4 | Reporting Engine → reader | Reports, screenshots | Leaking data in artefacts | Redaction of artefacts, review before sharing |

## 3. Module responsibilities
| Component | Responsibility | Inputs | Outputs | Security / ethics duty | Main FR/NFR |
|---|---|---|---|---|---|
| Requirement Analyzer | Structure requirements and assign IDs | Requirement text | Requirement records | Validate and mask input; reject oversize or malformed input | FR-01 to FR-05; NFR-10 |
| Test Case Generator | Create traceable test cases | Requirement records | Test cases linked to requirement IDs | Human approval before use; log model, template version | FR-06 to FR-11; NFR-30, NFR-31 |
| Script Generator | Create executable scripts | Approved test cases | Playwright / Selenium PyTest scripts | Static check for forbidden calls; no secrets in output | FR-12 to FR-16; NFR-11 |
| Execution Engine | Run scripts, capture evidence | Scripts, configuration | Results, screenshots, logs | Run in isolation; public targets only | FR-17 to FR-21; NFR-11 |
| Self-Healing Engine | Repair broken locators | Failure context, DOM snapshot | Candidate locator, confidence score | Human approval for permanent change; record every healing | FR-22 to FR-26; NFR-31 |
| Failure Analyzer | Classify and explain failures | Results, logs, healing events | Failure classes, suggested causes | Mark output as advisory; log inputs | FR-27 to FR-29 |
| Reporting Engine | Build reports and metrics | SQLite data | HTML/Markdown/PDF reports | Redact secrets and sensitive data in artefacts | FR-31 to FR-33; NFR-29 |
| Dashboard | Show history and metrics | SQLite data | Charts and tables | Read-only access | FR-33 |
| LLM Gateway | Single path to the model | Masked prompt | Validated output | Retry, schema validation, audit, mock/cache fallback | FR-36, FR-37; NFR-13, NFR-25 |
| Data Masking and Validation Layer | Remove sensitive values; validate | Any text | Masked text | Fail closed on validation errors | FR-30; NFR-15, NFR-16 |
| SQLite Persistence | Store records | All modules | Queryable store | Parameterised queries; local file permissions | NFR-12, NFR-24 |
| Audit Logging | Record decisions | Events | Append-only log | No secrets in log | FR-37; NFR-14, NFR-34 |

*IDs checked against `architecture/02` and `03` on 14 Nov 2026. FR-34 (traceability) and FR-35 (CLI) belong to the Pipeline Orchestrator.*

## 4. Framework-specific risks and controls
| Risk (register ID) | How it arises in this framework | Control | Status |
|---|---|---|---|
| LLM data egress (R14) | Requirement text or test data goes to a third-party API | Masking before every call; synthetic/public data only; DPO consulted if real data is ever proposed | Implemented (P) for masking; data policy Designed-only |
| Prompt injection (R15) | Requirement text or page content contains instructions | Separate instructions from data; schema-validated outputs; approval gate | Implemented (P) |
| API key exposure (R16) | Key in repository, log or screenshot | Environment variables and GitHub Secrets; `.gitignore`; secret scan | Implemented (P) for env vars; scanner pending ADR-010 |
| Generated-code execution (R17) | LLM-written scripts run on the host | Static check; isolated environment; approval gate; public targets | Implemented (P): static check, approval; container isolation pending ADR-010 |
| Biased or wrong test output (R5) | Model omits cases or invents expectations | Human review; coverage ratio reported; limits stated | Implemented (P) |

## 5. Implemented versus designed controls
| Control | Status | Evidence to capture | Notes |
|---|---|---|---|
| Input validation and masking | Implemented (P) | Unit test; before/after screenshot | FR-02, FR-30, NFR-10, NFR-15 |
| Schema validation of LLM output | Implemented (P) | Unit test with malformed response | NFR-10 |
| Human approval gates | Implemented (P) | CLI screenshot | FR-10, NFR-31 |
| Audit log of LLM calls and healing | Implemented (P) | Log excerpt (no secrets) | FR-37, FR-25, NFR-14 |
| API key from environment variable | Implemented (P) | Code excerpt; `.gitignore` | NFR-09 |
| Parameterised SQL | Implemented (P) | Code excerpt; test | NFR-10 |
| Static check of generated scripts | Implemented (P) | Unit test | FR-15, NFR-11 |
| Encryption in transit | Inherited (I) | Library defaults; no custom code | HTTPS to API and GitHub |
| Encryption at rest (AES-256) | Designed-only (D) | None | SQLite file is not encrypted in the prototype |
| Role-based access control | Designed-only (D) | None | CLI single-user; NFR-27 |
| Multi-factor authentication, SSO | Designed-only (D) | None | Production deployment only |
| Penetration testing | Out of scope (X) | — | |
| Formal GDPR/ISO certification | Out of scope (X) | — | Standards used as guidance only |

## 6. Standards mapping (guidance only)
| Source | Used for | Register ID |
|---|---|---|
| NIST AI RMF 1.0 | Govern, map, measure, manage framing for AI risk | REF-201 |
| NIST CSF 2.0 | Security outcome categories for the controls table | REF-202 |
| OWASP Top 10 for LLM Applications | Prompt injection, insecure output handling, data disclosure | REF-203 (edition to be chosen) |
| OWASP Top 10 (web) | Input validation, injection, secrets | REF-204 (edition to be chosen) |
| GDPR | Data minimisation, lawful basis, purpose limitation | REF-205 |
| ISO/IEC 27001:2022 | Information security management controls | REF-206 |
| ACM Code of Ethics | Honesty, avoiding harm, privacy | REF-211 |

**Compliance caveat.** The framework uses these documents as design guidance. It makes no claim of compliance or certification. Questions about lawful basis, consent or data-processing agreements should be confirmed with the Data Privacy Officer or Legal before they appear in the final report.

## 7. Worked example (Test Case Generator and Script Generator)
A requirement states that a registered user can log in with a valid email and password. The Data Masking and Validation Layer masks any real-looking email address, and the LLM Gateway sends the masked text with template `tcg-v1` to the model. The response must match the test case schema (title, steps, test data, expected result, requirement ID); if it does not, the call is retried once and then rejected. The reviewer approves the test case, and the Script Generator produces a Playwright PyTest script. Before execution, a static check rejects any script that imports process or network modules. Related controls: GDPR data minimisation (REF-205) and ISO/IEC 27001 (REF-206) for guidance; OWASP LLM guidance for insecure output handling (REF-203).
