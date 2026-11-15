# UNIT 6 PLAN: Full System Integration, Performance Evaluation and Deployment Planning

**Repository copy of the workspace file `knowledge/UNIT6_PLAN.md` (ADR-023); keep both in step.** **Version:** 1.0 (planning, no code yet) · **Date:** 15 Nov 2026 · **Extends:** `IMPLEMENTATION_PLAN.md` §1 (Unit 6), `UNIT5_PLAN.md` (same format) · **Code work happens in:** the repository folder (`UoP_Capston_Project_dilip`), branch `develop` (ADR-028)
**Instruction file:** `01_UNIT_INSTRUCTIONS/Unit06_Integration_Feature_Completion_Evaluation.md`
**Two deliverables (two Word documents):**
1. **Parts A to C** (one document): A System Integration and Feature Completion, B System Evaluation and Metrics Reporting, C Deployment and Configuration Planning. The instruction file gives two different minimums (1,000 and 1,200 words) and a maximum of 1,500, excluding references and title; **target 1,300 to 1,450** so both are satisfied. Double-spaced Times New Roman 12 pt; all code and output screenshots inside the document, captioned.
2. **Part D** (separate document): Chapters 4 (Results), 5 (Discussion) and 6 (Conclusion) of the Capstone Project Report Template, consolidating Units 4, 5 and 6. The instruction file gives two different minimums (4,500 and 5,000) and a maximum of 6,000; **target 5,200 to 5,800**. Chapter 4 = 4.1 Implementation Overview, 4.2 Output and Screenshots, 4.3 Evaluation Metrics; Chapter 5 = 5.1 to 5.4; Chapter 6 = conclusion (`REPORT_STRUCTURE_MASTER.md`).
**Rubric rows:** A, B, C, D (each "all three tasks effectively completed"), Sources and Evidence, Connection to course materials.
**Due date:** TBD (not in instruction files). **Planning figure:** about 39 hours build and evidence plus write-ups (roadmap budget for Unit 6: 43 hours, the peak load).
**Unit 6 readings (course references, all Verified – Course):** Summers (2020) Ch. 8, software configuration management; LaunchNotes (2023), qualitative vs quantitative metrics (REF-020); Brown (2025), documentation best practices (REF-021); Bennett (2024), software configuration management (REF-022); Sumo Logic (n.d.), software deployment (REF-023); Wells (2025), software quality metrics (REF-024); Bytebytego (2023) video, deployment strategies (REF-025). Summers Ch. 8 needs its REF number confirmed in `MASTER_REFERENCES.md` before Cowork cites it. ADR-020 applies: course readings first.

## 1. Decisions to Make Before Coding (about 20 minutes; all recorded as proposed ADR-035 to ADR-040 in `PROJECT_DECISIONS.md`)

| # | Decision | Recommendation | Why |
|---|---|---|---|
| ADR-035 | Unit 6 scope tiers | **Must:** slices U6-1 to U6-6, U6-8 (evaluation), U6-10 (deployment pack), U6-11 (handoff). **Should:** U6-7 dashboard polish, PDF export, Selenium parity, `nightly-e2e.yml`, second public demo app. Descope order (ADR-018): dashboard polish, PDF export, Selenium parity. **Never drop:** Execution Engine, healing integration, the mutation harness and at least two measured metrics | Keeps Parts A to C and Part D answerable if time runs short |
| ADR-036 | Evaluation design | Mutation harness over the local sample app, at least 30 seeded mutations (id, class, XPath or structure, text) plus unmutated controls and assertion-defect controls; a labelled failure set of at least 40 failures labelled **by the student before running the classifier**; healing and false-heal rate, classification accuracy, non-LLM latency (p95), requirement coverage ratio, script executability, line coverage and CI status, authoring-time ratio, control status table (O1 to O8). Mock and live LLM results are reported **separately and labelled**. Missing a numeric target is a finding (RESEARCH_FRAME §5) | Reproducible, honest, and covers every objective; the labelling-first rule avoids circular accuracy |
| ADR-037 | Technology choices for Unit 6 | Execution through PyTest with Playwright first (Selenium parity is Should); `string.Template` for report templates (extends ADR-032, no Jinja2); **Pandas** for aggregation (approved); **matplotlib** for charts as an optional extra `report` in `pyproject.toml` (new dependency, charts only); PDF through Playwright `page.pdf()` from the HTML report (no new dependency); Dashboard is a static HTML page with pre-rendered charts, as designed in `04_COMPONENT_ARCHITECTURE.md` §3.8 | One new optional dependency; the design stays offline and small |
| ADR-038 | Docker (ADR-025 conditional) | Write the Dockerfile, `.dockerignore` and `.env.example`; **verify by a CI job that builds the image** because Docker is not installed on the laptop (ADR-027). Part C says so plainly; no local container run is claimed | Evidence without installing Docker Desktop on a managed laptop |
| ADR-039 | Three-session workflow and evidence rules | Coding session (this one, repository folder) → separate evidence session (Playwright, screenshots only) → Cowork (two documents). Evidence rules: anonymous (signed-out) captures, no bookmarks bar or personal data, no sign-in-only pages (Actions job logs need login, so the student captures those in a private window), URL banner injected, local `file://` pages for report and dashboard, CLI output as rendered committed logs labelled "log excerpt" unless the student captures a real terminal | Lessons from Unit 5 (bookmark leak, job-log login, stale contributor entry) |
| ADR-040 | Qualitative metric method | Structured rubric (clarity, completeness, actionability, each 1 to 5, with comments) applied to the HTML report and the dashboard by the student and, if available, up to two volunteer peers; consent record, no personal data, no client content (ADR-005). With no peers, report as self-review and state the limit in 5.3 | Satisfies "at least one qualitative metric" honestly (REF-020) |

**Open inputs for the student (not blockers for slice U6-1):** O-14 qualitative reviewers (peers or self only); O-10 how many external sources Chapter 5.2 may use (the Unit 6 course readings are about tooling and metrics, so a literature comparison needs the verified Chapter 2 sources; decide before Part D is written); O-16 due dates for Unit 6. See `PROJECT_DECISIONS.md`.

## 2. What the Rubric Needs (artefact checklist)

| Task | What must exist | Evidence | Produced by |
|---|---|---|---|
| A1 input-output examples | `aitaf run` pipeline: requirement text in, results, healing events, analysis, report and dashboard out, on the sample app; code and output | E10, E11, E12 | U6-3 to U6-9 |
| A2 key code per module | Screenshots of main logic of Execution Engine, healing integration, Failure Analyzer, Reporting Engine, Dashboard, evaluation harness, each with a short explanation | E12 | Evidence session |
| A3 inter-module communication | Excerpts: gateway call (API request), repository read and write (SQLite), report/dashboard reading stored runs (UI-backend link), engine to healer interface | E12 | Slices U6-3 to U6-7 |
| B1 two or more quantitative metrics with screenshots | Healing success and false-heal rate, classification accuracy, latency p95, coverage ratio, executability, coverage; raw CSV; computed by `aitaf metrics`/`evaluate` | E13 | U6-8 |
| B2 one or more qualitative metrics with screenshots | Rubric scores on report and dashboard; consent record if peers | E14 | U6-8, student |
| B3 table, chart, interpretation | Results table (measured versus target), at least two charts, 3 to 5 sentences each | E13 | U6-8 (charts), Cowork (text) |
| C1 deployment methods and choice | Comparison of cloud, on-premise, Docker (REF-023, REF-025); Docker chosen for the prototype | text | Cowork |
| C2 configuration management | How `.env`, `Settings`, `pyproject`, CI and tags support reliability (REF-022, Summers Ch. 8) | text | Cowork |
| C3 setup requirements | Prerequisites, environment variables, install, build and deployment commands, all verified by running them (or by CI for Docker) | E15 | U6-10 |
| D Results, Discussion, Conclusion | Chapters 4 to 6 from the evidence above; limits and future work stated | E04 to E15 | Cowork |
| Sources and course connection | REF-020 to REF-025 plus Summers Ch. 8; earlier unit sources only through Chapter 2 | none | Cowork |

## 3. Evaluation Design (objectives O1 to O8; see `RESEARCH_FRAME.md` §4)

| Objective | Metric and target | Method in Unit 6 | Data and tool |
|---|---|---|---|
| O1 coverage | Requirement coverage ratio at least 90% of 20 requirements with an approved test case | Extend the sample set to 20 requirements; run analyzer and generator; approve cases (human gate) | `aitaf metrics`, CSV |
| O2 executability | At least 80% of generated scripts run without syntax, import or framework errors | Execute every generated script on the sample app with Playwright | Execution Engine results |
| O3 healing | At least 70% success, at most 5% false heals over at least 30 seeded mutations | Mutation harness (FR-38): catalogue with seed; healing run per mutation; success = healed locator resolves to the intended element and passes validation; false heal = wrong element accepted | `evaluation/` harness |
| O4 classification | At least 75% agreement on at least 40 labelled failures | Student labels failures first; classifier runs after; confusion matrix | `evaluation/labels.csv` |
| O5 latency | Non-LLM operations under 5 s for 95% of runs (NFR-01); LLM latency separate (ADR-007) | Metrics hooks (already in Unit 5) over at least 30 pipeline runs; report p50, p95 | `core/metrics` |
| O6 quality | Line coverage at least 80% (core 97.86% at v0.5.0); CI green on `develop` | pytest-cov and CI run page | E08, CI |
| O7 authoring effort | At most 50% of manual time for the same 10 requirements | Student stopwatch: manual test-case writing versus tool run plus review. **Student task**; may be descoped and reported as not measured | `evaluation/authoring_time.csv` |
| O8 controls | At least six controls Implemented with evidence | Control status table from `architecture/07` with test or screenshot per row | table |

Reporting rule: every number says whether it came from the **mock** or the **live** provider; one live evaluation run only (ADR-026, $5 cap, responses cached).

## 4. Build Slices (one slice per Claude Code session)

Each slice: tests first from the FR acceptance criteria, then code, then the closing ritual (§7). Hours are estimates.

| # | Tier | Slice | Requirements | Tests | Evidence | Hours |
|---|---|---|---|---|---|---|
| U6-0 | Must | Housekeeping: pull `develop`, revert stray `.gitignore` line, confirm CI green, confirm `OPENAI_API_KEY` is set (never print it), `openai` and `pandas` in `requirements.txt`, Playwright browsers present, confirm ADR-035 to ADR-040 | — | — | — | 0.5 |
| U6-1 | Must | OpenAI provider behind the gateway, retry with back-off (NFR-06), response cache (ADR-026), cost and token capture, live smoke test (E04b) within the cap | FR-35 to FR-37, NFR-06, NFR-25 | Provider contract tests with a fake HTTP layer; retry and cap tests; smoke test marked `live` and excluded from CI | E04b | 3 |
| U6-2 | Must | Local sample web app (standard-library server: login, product list, cart, checkout) with a mutation switch, plus the 20-requirement set and DOM fixtures from it | FR-38 (part), NFR-08 | App route tests; every locator reachable | sample app screenshot | 3 |
| U6-3 | Must | **Execution Engine** on Playwright: runner via PyTest, allow-list guard, screenshot on failure, persistence of run and results, headless, timeouts, retries; Selenium parity is Should | FR-17 to FR-21, NFR-04, 08, 11, 23 | Black-box (allow-list abort, screenshot linked, results queryable after exit); white-box (hooks) | E10a | 5 |
| U6-4 | Must | **Healing integration**: engine calls the healer on locator failures, records proposed events, approval gate, per-step and per-run limits, healing success rate in results | FR-25, FR-26, NFR-03, NFR-18 | Black-box on the sample app with mutated pages; negative case (wrong element, assertion defect) | E09b | 4 |
| U6-5 | Must | **Failure Analyzer**: deterministic pre-classifier, LLM reasoning for ambiguous cases (mock by default), clustering, confidence, redaction before LLM | FR-27 to FR-30, NFR-10, 15, 18 | Fixture set; every failure gets a category and score; redaction test | E10 | 4 |
| U6-6 | Must | **Reporting Engine**: one report data model, HTML (offline, links screenshots and healing events and analysis), Markdown; metrics computation; PDF through `page.pdf()` is Should | FR-31, FR-32, FR-34, FR-39 | HTML opens offline; identical figures across formats; metrics match stored data | E11 | 4 |
| U6-7 | Should | **Dashboard**: static HTML with Pandas aggregation and pre-rendered charts (pass rate, healing, accuracy, coverage, executability, cost, trend) | FR-33, NFR-29 | Chart files exist; trend across at least three runs | E11 | 3 |
| U6-8 | Must | **Evaluation harness**: mutation catalogue (at least 30) with seed, labelled failure set (at least 40), `aitaf evaluate`, raw CSV, results table, charts; one live run; qualitative rubric sheet | FR-38, FR-39, NFR-01 | Same seed gives same mutations; metrics reproduce from stored data | E13, E14 | 5 |
| U6-9 | Must | `aitaf run` orchestrated pipeline, integration tests, `integration.yml` (Playwright on Ubuntu), optional `nightly-e2e.yml`; **tag `v1.0.0-rc1` on `develop`** (ADR-033) | FR-34, NFR-05, NFR-08 | Integration marker; end-to-end on the sample app | E12, E17c | 3 |
| U6-10 | Must | Deployment pack: Dockerfile, `.dockerignore`, `.env.example`, `docs/user-guide/DEPLOYMENT.md` (prerequisites, variables, install and build commands), CI job that builds the image | NFR-05, NFR-19, NFR-20 | Config validation tests; `docker build` in CI | E15 | 2 |
| U6-11 | Must | Evidence and handoff: `UNIT6_HANDOFF.md`, `UNIT6_SCREENSHOT_GUIDE.md`, evidence session brief, two Cowork prompts, progress log, register, CHANGELOG | — | — | E10 to E15 registered | 3 |

Total about 39.5 hours. Public second demo app (for success criterion (b), two public demo applications): optional slice inside U6-8, only against an allow-listed public practice site, never a client system (ADR-005).

## 5. Slice Prompt Template (paste into Claude Code in the repository folder)

```text
Slice U6-<n>: <module>. Requirements: <FR and NFR IDs>.
Read only: docs/architecture/04_COMPONENT_ARCHITECTURE.md section <x>, the FR/NFR rows for these IDs (grep), and knowledge-base pointers in CLAUDE.md. Plan: Unit 6 plan in the workspace (knowledge/UNIT6_PLAN.md) section 4, row U6-<n>.
Write the tests first from the acceptance criteria (mark each test blackbox or whitebox; integration tests marked integration), then the code in src/aitaf/<package>, then run: ruff check, ruff format --check, mypy src, pytest with coverage, pip-audit, python -m aitaf.quality.import_rules.
Docstrings cite the FR/NFR IDs. Coverage at or above 80% (90% for healing). Live LLM calls only in the slices named in the plan and within the $5 cap; never print or log the API key. Then do the closing ritual (progress log row, register evidence, CHANGELOG), commit to develop with a Conventional Commit and Refs line, push, report the CI result. No AI attribution in commits, tags or pull requests.
```

## 6. Three-Session Workflow (who does what)

| Session | Opens | Does | Does not |
|---|---|---|---|
| **Coding session** (Claude Code, repository folder) | repository | Slices U6-0 to U6-11; at the end, writes `UNIT6_HANDOFF.md`, `UNIT6_SCREENSHOT_GUIDE.md` and the evidence brief with exact URLs, tag, CI run numbers and local pages to capture | Take screenshots |
| **Evidence session** (new Claude Code session, repository folder) | repository | Screenshots only with Playwright (GitHub pages signed out, local `file://` report and dashboard, rendered log excerpts), following the brief and ADR-039 rules | Change code, docs or `.gitignore`; commit |
| **Cowork** (workspace plus repository access) | workspace | Writes the two documents from the handoff, guide, progress log, register and screenshots, with the prompts below (final text produced in U6-11) | Invent results, issues or references |

Student checkpoints: after U6-8 (label the 40 failures before the classifier runs; run the stopwatch measurement; complete or arrange the qualitative review); after U6-11 (capture the sign-in-only pages in a private window, check every screenshot, then run Cowork and review both documents; the author is responsible for content, ADR-009).

**Cowork prompt skeleton (completed in U6-11):** two prompts, one per document. Document 1 (Parts A to C): read the Unit 6 instruction file, `UNIT6_HANDOFF.md`, the guide's coverage matrix and figure captions, `PROGRESS_LOG.md` (only source of issues and challenges), the register and screenshots, `RESEARCH_FRAME` §4, and REF-020 to REF-025 plus Summers Ch. 8; 1,300 to 1,450 words; sections A1 to C3 in order; every figure captioned and labelled mock or live; follow the do-not-claim list; end with a word count, coverage checklist and missing-figure list. Document 2 (Part D): the same sources plus the Unit 4 and 5 handoffs and Chapters 1 to 3 notes in `final-report/`; Chapters 4 to 6 with the template's numbering; 5,200 to 5,800 words; limitations from the handoff; earlier-unit sources only as allowed by decision O-10.

## 7. Knowledge Update Protocol (same ritual as Unit 5, plus)

Closing ritual for every slice: five local checks green and CI green; one row in `docs/project-management/PROGRESS_LOG.md` (real issues and challenges only); register evidence in `evidence/EVIDENCE_REGISTER.md`; CHANGELOG line; commit and push to `develop`.
Unit 6 additions: record every number with its provider (mock or live) and date; after each slice update the **do-not-claim list** in the handoff draft; keep `evaluation/` data files and the CSVs committed so Cowork can cite them; update `CURRENT_UNIT.md` and `CAPSTONE_STATUS.md` after U6-8 and at the end of the unit; add ADRs the same day (library, scope, evaluation changes).
End of Unit 6: update `PROJECT_ROADMAP.md` M11 to M14 and E10 to E15; copy reusable text into `final-report/CHAPTER4_RESULTS.md` (4.1 to 4.3) notes; copy changed design documents between repository and workspace (ADR-023).

## 8. Risks Specific to Unit 6

| Risk | Mitigation |
|---|---|
| Healing or classification misses its numeric target | Report it as a finding with the threshold tuning described (thresholds are initial values, see Unit 5 handoff); tune on a **separate** tuning set, report on the evaluation set; never adjust targets afterwards |
| Circular accuracy (labels written by the system) | Student labels the failure set before running the classifier (ADR-036) |
| Mock results mistaken for model results | Label provider on every table, chart and caption; one live run only, reported separately |
| Public demo site unavailable or changes | The local sample app is the primary system under test; the public site is optional and allow-listed |
| Flaky browser tests in CI | Retries recorded, headless Chromium only in CI, integration job separate from the unit-test job |
| API cost over cap | Cache, call cap, cheap model, live runs only in named slices |
| Docker not installed locally | CI builds the image; Part C states exactly what was and was not run (ADR-038) |
| Screenshot leaks personal or employer data (bookmarks bar, avatar, paths) | ADR-039 rules; student checks every image before commit |
| Word-count ambiguity in the instruction file | Targets chosen to satisfy both stated minimums |
| Unit 5 paper still pending | Does not block Unit 6 code; keep Unit 5 handoff and evidence frozen at `v0.5.0` |
