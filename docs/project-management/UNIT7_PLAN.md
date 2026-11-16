# UNIT 7 PLAN: System Testing, Maintenance Planning and Initial Project Report

**Version:** 1.0 (planning, no code yet) · **Date:** 16 Nov 2026 · **Extends:** `IMPLEMENTATION_PLAN.md` §1 (Unit 7), `UNIT6_PLAN.md` (same format) · **Code work happens in:** `C:\Users\dchennap\repos\UoP_Capston_Project_dilip`, branch `develop` (ADR-028)
**Instruction file:** `01_UNIT_INSTRUCTIONS/Unit07_Testing_Maintenance_Documentation.md`
**Two deliverables (two Word documents):**
1. **Parts A and B** (one document): A System Testing and Documentation (system testing, test documentation, evaluation), B System Maintenance Plan (maintenance strategy, maintenance documentation, risk identification and mitigation). 1,000 to 1,500 words excluding references and title; **target 1,300 to 1,450**. Double-spaced Times New Roman 12 pt; all code and output screenshots inside, captioned.
2. **Part C** (separate document): the initial project report, Chapters 1 to 6 with preliminary sections (title page, abstract, acknowledgements, contents, lists of tables and figures, abbreviations) and additional sections (references in APA 7, appendices) following the Capstone template. **8,000 to 12,000 words; target about 9,500 to 10,500** (`MASTER_PLAN.md` §9.2 budgets about 9,500 for the Unit 7 version). It combines the Week 3 documents (Units 1 to 3: introduction, design) and the Week 6 documents (Unit 6 Parts A to D), adds the Unit 7 test results to Chapter 4, incorporates instructor feedback, and is the base of the Unit 8 final report (13,000 to 15,000 words).
**Rubric rows:** A, B, C (each "all three tasks effectively completed"), Sources and Evidence, Connection to course materials.
**Due date:** TBD (O-17). **Planning figure:** about 27 hours build and evidence plus write-ups (roadmap budget for Unit 7: 29 hours).
**Unit 7 readings (supplied in the instruction file; already in `MASTER_REFERENCES.md` as REF-026 to REF-030, Verified – Course, ADR-020):** Hrupa (2024), what is system testing; BrowserStack (2025), what is system testing; Miller (2024), capstone project outline essentials; Thales (n.d.), four types of software maintenance; 5-Minute Lessons by Victor (2024) video on the same four types. Chapter 2 needs more sources than the readings give: see ADR-050 and O-10.

## 0. Where Unit 6 left us (facts the plan builds on)

- Release candidate `v1.0.0-rc1` (commit 86a6095), CI, Integration and Release green. 1,381 tests (845 black-box, 536 white-box; 8 real-browser), coverage 94%.
- Existing test levels: unit tests, cross-module tests with fakes, 8 real-browser integration tests, the evaluation harness. **No formal system test suite, no acceptance tests tied to the FR acceptance criteria, no consolidated test summary report and no defect log.** That is the Part A gap.
- **Known defects and limits found in Unit 6 (the real material for "bugs found and how they were resolved"):** (1) the report and Dashboard "script executability" counts a script with a missing locator as executable (100%) while the evaluation figure is 38.9% mock, 33.3% live; (2) the healer proposed an opposite-action replacement (a "remove" button replaced by the "add" button, confidence 0.65) and the false-heal control had the same shape; (3) the report summary does not state the main problem; (4) tracebacks carry raw object reprs (`object at 0x...`); (5) "Healing success rate" counts proposed, not verified, repairs and "API cost per run" divides by the two runs involved; (6) the Dashboard has no link to run reports and no code coverage (FR-33 partly); (7) Selenium never ran in a real browser (FR-13, FR-17 partly). Already fixed in Unit 6: relative evidence paths in the container, the release guard on the first tag, mypy in CI.
- Maintenance-relevant warnings already visible: CI warns that Node.js 20 actions are deprecated and that `ubuntu-latest` moves to Ubuntu 26 from 19 Oct 2026; dependencies are pinned and audited by `pip-audit`.
- The living manuscript `final-report/` is thin: Chapters 1 and 3 about 700 to 800 words, Chapter 2 a skeleton (879 words, "full texts to be read"), Chapter 4 to 6 skeletons. The real text for Chapters 4 to 6 lives in `Submissions/UNIT6_Doc2_PartD_Chapters_4-6.docx`; for Chapters 1 to 3 in `Submissions/Revised/` (Units 1 to 3).

## 1. Decisions to Make Before Coding (about 20 minutes; recorded as proposed ADR-045 to ADR-050 in `PROJECT_DECISIONS.md`)

| # | Decision | Recommendation | Why |
|---|---|---|---|
| ADR-045 | Unit 7 scope tiers | **Must:** U7-1 defect fixes, U7-2 system tests, U7-3 acceptance tests, U7-4 test-level runner and summary report, U7-5 defect log, U7-6 maintenance plan and its automation, U7-7 report assembly kit, U7-8 handoff. **Should:** Dashboard code-coverage tile and report links (FR-33), nightly full-pipeline workflow, Selenium in a real browser, performance over 30 runs. **Never drop:** system tests, acceptance matrix, defect log, maintenance plan | Keeps Parts A to C answerable if time is short; descope order: Selenium, performance runs, Dashboard tile |
| ADR-046 | What each test level means in this project | Unit (exists, 1,373); integration (cross-module with fakes plus 8 real-browser tests); **system** (the whole pipeline in Chromium on the demo shop, including failure scenarios); **acceptance** (one automated check per FR acceptance criterion, run by the author as customer, plus a short manual checklist for the report and Dashboard); regression (golden-run comparison and the full suite on every push); performance (latency samples over repeated runs against NFR-01); stability (repeat the same run N times, compare outcomes, NFR-08) | The assignment asks for "multiple levels as appropriate"; this maps each to something that already exists or is cheap to build |
| ADR-047 | Acceptance testing method | Criteria-based from the FR table's acceptance column, automated where possible; the author is the acceptor and says so (as with the self-review in Unit 6). **Decided 16 Nov (student): self-review only, no volunteers**; the document says so and states the limit (one acceptor who is the author) | Honest and finishable; no invented users |
| ADR-048 | Defect log and fix policy | `docs/project-management/DEFECT_LOG.md` with IDs, found-by, severity, status, fix commit, regression test. Seed it from the real Unit 6 findings; add only defects the Unit 7 tests actually find. Fix Must-severity defects with a regression test; document the rest as known limitations. A fix that changes a metric definition is recorded in the changelog and the earlier figures stay as published | The log is the evidence for "bugs found and resolved"; no defect may be invented |
| ADR-049 | Maintenance plan scope | Document (`docs/maintenance/MAINTENANCE_PLAN.md`) plus minimal automation: Dependabot configuration, issue templates for bug and enhancement, a scheduled workflow (weekly audit and pipeline run on the demo shop), a release checklist. The four maintenance types each get a concrete example from this project | A plan that the repository actually runs is stronger than prose |
| ADR-050 | Report assembly and Chapter 2 sources | Markdown living manuscript in `final-report/` is the single source; Unit 1 to 6 documents are mined for text, never rewritten from scratch; Cowork assembles the Word file. Chapter 2 may use up to about 10 additional sources; every one must be verified by the author (link opens, details match) before it enters `MASTER_REFERENCES.md`; unverified claims stay marked | Part C needs a real literature review and the rubric rewards sources, but invented references are forbidden (ADR-009) |

**Open inputs for the student (not blockers for U7-0):** O-10 literature depth (answer before Chapter 2 is written); O-16 and O-17 due dates for Units 6 and 7; **instructor feedback** from Units 3 to 6 (the feedback log in `PROJECT_DECISIONS.md` is empty; Part C must incorporate it); O-1 and O-2 (term dates, supervisor and chair names) for the title page; wording of the acknowledgements.

## 2. What the Rubric Needs (artefact checklist)

| Task | What must exist | Evidence | Produced by |
|---|---|---|---|
| A1 system testing at several levels | Integration, system and acceptance runs with pass and fail output; screenshots or logs | E16 | U7-2 to U7-4 |
| A2 test documentation | Test summary report: objectives, scope, test cases, procedures, results; bugs, issues and limitations with resolutions (defect log) | E16, `TEST_SUMMARY_REPORT.md`, `DEFECT_LOG.md` | U7-4, U7-5 |
| A3 evaluation | Short reflection on how comprehensive testing supports reliability and quality, with the project's own examples | text | Cowork |
| B1 maintenance strategy | The four types with project examples; schedule for monitoring, updates and performance checks | `MAINTENANCE_PLAN.md`, scheduled workflow | U7-6 |
| B2 maintenance documentation | Version updates (SemVer, changelog, tags, releases), bug fixes and enhancement requests (issue templates), how Git and configuration management support them | `MAINTENANCE_PLAN.md`, `.github/` | U7-6 |
| B3 risks and mitigation | Likely post-deployment risks (dependency vulnerabilities, API change and cost, data inconsistency, usability, CI platform changes) with mitigations and contingency | risk table | U7-6 |
| C1 preliminary sections | Title page, abstract (250 words or fewer), acknowledgements, contents, lists of tables and figures, abbreviations | `final-report/`, glossary | U7-7, Cowork |
| C2 core chapters | Chapters 1 to 6 per template; Chapter 4 includes the Unit 7 test results; instructor feedback incorporated | `final-report/`, Unit 3 and 6 documents | Cowork |
| C3 additional sections | APA 7 references with working links; appendices (screenshots, logs, data samples) | register, `MASTER_REFERENCES.md` | U7-7, student |
| Sources and course connection | Unit 7 readings plus verified extra sources; explicit links to the readings | none | Cowork |

## 3. Test Design (what U7-2 to U7-4 build)

**System scenarios (`tests/system/`, marker `system`, mock provider, real Chromium, demo shop):**

| ID | Scenario | Checks (FR and NFR) |
|---|---|---|
| S1 | Happy path: `aitaf run` on the 20 requirements | 54 cases and scripts, results stored, report, Dashboard, traceability from result back to requirement (FR-34, FR-35) |
| S2 | Mutated shop with `--heal` | Locator failures offered to the healer; events stored; originals unchanged (FR-22 to FR-25) |
| S3 | Human gate: run without `--approve-all` | Stops after generation; nothing scripted (FR-10, FR-11) |
| S4 | Provider failure | Gateway falls back to mock; audit says `fallback` (FR-36, FR-37, NFR-06) |
| S5 | Hostile and invalid input | Injected requirement rejected; empty file reported with exit code 2 (FR-30, NFR-10, NFR-13) |
| S6 | Blocked host | Execution refuses a host outside the allow-list before anything starts (FR-21) |
| S7 | Interrupted run | A killed run is reported INCOMPLETE and the database stays valid (NFR-07) |
| S8 | Repeatability | The same run twice gives the same counts and categories (NFR-08) |
| S9 | Approval gap | `approve-heal` moves the stored locator to a new version and patches the scripts (FR-25) |
| S10 | Container smoke | Image builds and runs the pipeline (CI job, already exists) |

**Acceptance tests (`tests/acceptance/`, marker `acceptance`):** one test per FR group, IDs `AT-FR-nn`, written from the FR table's acceptance column; the generated matrix `docs/project-management/ACCEPTANCE_MATRIX.md` lists FR, criterion, test ID, result. Manual checklist (about 10 items) for what a machine cannot judge: report readable in one minute, Dashboard understandable, screenshots have text alternatives, next steps make sense.
**Regression:** a committed golden-run file of key counts (tests, passes, categories) compared with a tolerance; the whole suite on every push (exists).
**Performance and stability:** report and Dashboard build time over at least 10 repeated runs (NFR-01, p95); the same run repeated 5 times for outcome stability; optional worker scaling 1 versus 4 (NFR-23).
**Test-level runner:** `scripts/run_test_levels.py` runs every level, collects counts, durations and failures and writes `reports/test_summary/` plus `docs/project-management/TEST_SUMMARY_REPORT.md` (objectives, scope, procedure, results per level, defects, limits). Its output is evidence E16.

## 4. Build Slices (one slice per Claude Code session)

| Slice | Tier | Content | FR and NFR | Done when | Evidence | Hours |
|---|---|---|---|---|---|---|
| U7-0 | Must | Housekeeping: CI green, Cowork review of the Unit 6 documents applied, instructor feedback entered in the log, version plan for `1.0.0-rc2`, Chapter 2 source map and reading-notes template in place (see section 11) | NFR-20 | Five local checks green; log updated | none | 1 |
| U7-1 | Must | **Defect fixes from Unit 6** with a regression test each: executability definition shared by report, Dashboard and evaluation (D-001); opposite-action guard in the healer, then rerun the healing evaluation and record the effect (D-002); report summary states the main problem (D-003); object reprs stripped from log excerpts (D-004); metric labels and bases clarified (D-005) | FR-12, FR-23, FR-31, FR-39, NFR-29 | Tests red then green; healing evaluation rerun; changelog entry; old figures kept as published | E16 (fix log) | 4 |
| U7-2 | Must | System scenarios S1 to S9 in `tests/system/` | FR-10 to FR-25, FR-30, FR-34 to FR-37, NFR-06 to NFR-08, NFR-10 | Scenarios pass locally and in `integration.yml`; failures found are logged as defects | E16 | 4 |
| U7-3 | Must | Acceptance tests and `ACCEPTANCE_MATRIX.md`; manual checklist | FR-01 to FR-39 | Every FR has a test ID or a stated reason; matrix generated | E16 | 4 |
| U7-4 | Must | `scripts/run_test_levels.py`, golden run, repeated-run performance and stability, `TEST_SUMMARY_REPORT.md` | NFR-01, NFR-08, NFR-23 | One command produces the summary with counts per level | E16 | 3 |
| U7-5 | Must | `DEFECT_LOG.md`: seed with the Unit 6 findings, add what U7-1 to U7-4 found, status and regression test per entry; known-limitations list | NFR-20 | Every entry traceable to a commit or a stated limitation | E16 | 2 |
| U7-6 | Must | `MAINTENANCE_PLAN.md`, `dependabot.yml`, issue templates, scheduled workflow, release checklist, post-deployment risk table | NFR-05, NFR-12, NFR-20 | Plan covers four types, schedule, versioning, change requests, risks; workflow runs once | E16a | 3 |
| U7-7 | Must | Report assembly kit: update `final-report/` blocks from the Unit 1 to 6 documents, `GLOSSARY.md`, abbreviation list, figure and table list, appendices map, reference consolidation, achieved-versus-planned Gantt (E18), word budget table | NFR-20 | Each chapter block has source files and word targets; glossary checked | none | 3 |
| U7-8 | Must | `UNIT7_HANDOFF.md`, `UNIT7_SCREENSHOT_GUIDE.md`, evidence brief, two Cowork prompts, version `1.0.0-rc2` and tag, CHANGELOG, register | none | E16, E16a registered; tag published by the release workflow | all | 3 |

## 5. Slice Prompt Template (paste into Claude Code in the repository folder)

```text
Slice U7-<n>: <topic>. Requirements: <FR and NFR IDs>.
Read only: the FR/NFR rows for these IDs (grep), docs/project-management/DEFECT_LOG.md when it exists, and knowledge-base pointers in CLAUDE.md. Plan: Unit 7 plan in the workspace (knowledge/UNIT7_PLAN.md) section 4, row U7-<n>.
Write the tests first (mark each blackbox or whitebox; system tests marked system, acceptance tests acceptance), then the fix or code, then run: ruff check, ruff format --check, mypy src, pytest with coverage, pip-audit, python -m aitaf.quality.import_rules.
Docstrings cite FR/NFR IDs. Coverage at or above 80%. Record every real defect in the defect log with the commit that fixed it; never invent a defect. Then do the closing ritual (progress log row, register evidence, CHANGELOG), commit to develop with a Conventional Commit and Refs line, push, report the CI result. No AI attribution in commits, tags or pull requests.
```

## 6. Three-Session Workflow (who does what)

| Session | Opens | Does | Does not |
|---|---|---|---|
| **Coding session** (repository folder) | repository | Slices U7-0 to U7-8; writes the handoff, guide, evidence brief and prompts | Take screenshots |
| **Evidence session** (new session, repository folder) | repository | Screenshots only (GitHub signed out, local pages, rendered logs) per the brief and ADR-039 | Change code or docs; commit unless asked |
| **Cowork** (workspace plus repository) | workspace | Writes document 1 (Parts A and B) and document 2 (Part C) from the handoff, guide, logs, register and the Unit 1 to 6 documents; then a separate review pass | Invent results, defects or references |

Student checkpoints: now (decisions, instructor feedback, O-10, due dates); after U7-1 (check the fixes and the changed figures make sense to you); after U7-5 (read the defect log: is each defect real and fairly described?); after U7-7 (read the chapter source map and check every extra reference yourself); after U7-8 (screenshots, sign-in-only pages, Cowork, review prompt, then your own read against the do-not-claim list; the author is responsible for content, ADR-009).

**Cowork prompt skeleton (completed in U7-8):** Document 1 (Parts A and B): read the Unit 7 instruction file, `UNIT7_HANDOFF.md`, the guide's coverage matrix and captions, `TEST_SUMMARY_REPORT.md`, `DEFECT_LOG.md`, `ACCEPTANCE_MATRIX.md`, `MAINTENANCE_PLAN.md`, the register and screenshots, and the Unit 7 readings; 1,300 to 1,450 words; sections A1 to B3 in order; follow the do-not-claim list. Document 2 (Part C): the Unit 7 instruction file, the Capstone template, the chapter source map in the handoff, `final-report/`, the Unit 1 to 3 revised documents, the Unit 6 documents and their author notes, `PROJECT_DECISIONS.md`, `MASTER_REFERENCES.md`, instructor feedback; produce all preliminary and additional sections; 8,000 to 12,000 words; verified references only; end with a word count per chapter, a list of every instructor-feedback item and where it was addressed, and an author-notes page.

## 7. Report Assembly Map for Part C (about 9,500 to 10,500 words)

| Section | Words | Main source | Work needed |
|---|---|---|---|
| Abstract | 250 | Units 6 and 7 results | Write last, with measured numbers and the limits |
| Ch 1 Introduction | 1,200 | Unit 1 and 2 revised documents | Align with the final objectives O1 to O8; stakeholders; scope and limits as built |
| Ch 2 Literature review | 1,800 | Unit 1 literature, `final-report/CHAPTER2`, new verified sources | **Largest gap**: needs read sources, comparison table, research gap; O-10 |
| Ch 3 System design and methodology | 1,800 | Unit 3 documents, Unit 4 CI/CD, Unit 5 Git model | Mark controls Implemented or Designed-only as built; add the deployment view |
| Ch 4 Results and evaluation | 2,300 | Unit 6 Part D (about 2,000) plus Unit 7 test results | Add test levels, pass and fail counts, defect summary; keep tuned and independent results apart |
| Ch 5 Discussion | 1,300 | Unit 6 Part D, maintenance and limitations | Add maintenance implications and the comparison with Chapter 2 |
| Ch 6 Conclusion | 700 | Unit 6 Part D | Update contributions and future work |
| References, appendices | not counted | register, `MASTER_REFERENCES.md` | Appendix A code, B test results, C logs and evidence, D other |

Instructor feedback from Units 3 to 6 is entered in the feedback log first (Cowork cannot guess it); each item is mapped to a chapter and to a sentence that answers it.

## 8. Knowledge Update Protocol

Closing ritual for every slice: five local checks green and CI green; one row in `PROGRESS_LOG.md` (real issues only); the defect log updated; evidence registered; CHANGELOG line; commit and push to `develop`. Unit 7 additions: every number carries its provider and date; the do-not-claim list in the handoff is updated after each slice (especially after any metric definition changes); keep Unit 6 evidence as published (do not regenerate E10b or E11b for the Unit 6 documents); add ADRs the same day. End of unit: update `PROJECT_ROADMAP.md` M15 to M17 and E16, E18; update `CURRENT_UNIT.md` and `CAPSTONE_STATUS.md`; tag `v1.0.0-rc2` on `develop`, and the snapshot tag `unit7-submitted` after submission.

## 9. Risks Specific to Unit 7

| Risk | Mitigation |
|---|---|
| Fixing defects changes numbers already used in the Unit 6 documents | Keep the Unit 6 figures as published; record the change and the date in the changelog and defect log; show before and after in Chapter 4 |
| System tests are slow or flaky in CI | Separate marker and job, retries recorded, headless Chromium only, scenarios kept small |
| Defects invented to look thorough | Defect log only from real findings, each with a commit; "no defect found" is acceptable for a scenario |
| Chapter 2 weak or built on unverified sources | Author verifies each source; claims without a verified source are marked; O-10 answered early |
| Part C below 8,000 words or inconsistent between chapters | Word budget table, glossary check, Cowork review pass before the author edits |
| Instructor feedback missing or late (R12) | Enter it in the log as soon as it arrives; the plan does not block on it, the Cowork prompt lists any item still open |
| Executability fix lowers the headline number in the Dashboard and report | Expected: the stricter figure matches the evaluation (38.9% mock); state it as a correction in Chapter 5 |
| Docker still not tested locally | CI evidence remains the record; say so (ADR-044) |

## 10. Definition of Done for Unit 7

All Must slices done; CI, Integration and Release green; `TEST_SUMMARY_REPORT.md`, `DEFECT_LOG.md`, `ACCEPTANCE_MATRIX.md` and `MAINTENANCE_PLAN.md` committed; E16 registered; `1.0.0-rc2` tagged and released; handoff, guide, brief and two prompts written; instructor feedback logged; your open decisions answered or marked with the default applied.

## 11. Closing the Chapter 2 gap (do this before Chapter 2 is written; about 7 to 10 hours of student time)

State today: `final-report/CHAPTER2_LITERATURE_REVIEW.md` has 16 verified research sources (REF-101 to REF-116, claims limited to their abstracts), 15 standard documents (REF-201 to REF-215, URLs to test), the course readings, and **four quarantined entries (REF-Q01 to Q04) that must never be cited**. Empty slots: 2.1.4 requirements-to-tests study, 2.1.6 failure triage or log analysis study, commercial AI testing platforms (vendor pages), 2.1.7 and 2.1.8 depth, the 2.2 table cells and its interpretation paragraph, and numbers from the literature for the Chapter 5.2 comparison.

| Step | Who | What | Time |
|---|---|---|---|
| 1 | Student | Answer O-10 (recommended: up to about 10 additional sources, each verified) | 10 min |
| 2 | Coding session (slice U7-0) | `final-report/CHAPTER2_SOURCE_MAP.md`: per subsection the verified sources, what each may support, the empty slots with search terms, and a reading-notes template | 1.5 h |
| 3 | Student | Read six core sources in full (Wang 2024; Garousi and Mäntylä 2016; Leotta 2015; Stocco 2018; Parry 2022; Nass 2021) and skim the rest; fill one reading-notes entry each: question, method, key findings with section or page, limits, link to gaps G1 to G4 | 4 to 5 h |
| 4 | Student, then coding session | Fill the empty slots with new sources: search the UoP library, Google Scholar, ACM and IEEE, arXiv; open the link, copy details from the publisher record, check title, authors, year and venue; add as REF-117 onward with status Verified – Record checked; test every Standard URL (REF-201 to REF-215) and record the access date | 2 h |
| 5 | Cowork | Write Chapter 2 only from the reading notes and the library (1,800 words for Unit 7, 3,000 for Unit 8), fill Table 2 only with cited cells, phrase the gaps "in the sources reviewed", list every sentence it could not support | 1 h |
| 6 | Student | Trace each citation to a reading-notes line; remove or mark what you cannot trace; sign off; commit as v2.0 | 1.5 h |

Rules: no claim beyond what a read source says; no vendor performance claims without the vendor page cited as vendor-stated; Selenium and Playwright statements come from their documentation (REF-207, REF-208); never cite REF-Q01 to Q04; the literature comparison in Chapter 5.2 must state that studies differ in setting, so numbers are context, not a ranking.
