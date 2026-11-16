# Unit 6 handoff for writing the two documents

**Purpose:** everything needed to write the Unit 6 document 1 (Parts A to C: integration, evaluation, deployment) and document 2 (Part D: Chapters 4 to 6) without inventing anything. Quote only what is in this file, in `PROGRESS_LOG.md`, in `evaluation/results/RESULTS.md` or in the evidence files. Anything under "Do not claim" must not appear as an achievement.
**State described:** release candidate `v1.0.0-rc1` (commit `86a6095`, CI and Integration green, GitHub Release published as a prerelease), plus documentation commits after it. **Repository (public):** https://github.com/Deelip17/UoP_Capston_Project_dilip

## 1. Summary

All eight components now exist as working code and run together from one command, `aitaf run`: Requirement Analyzer, Test Case Generator, Script Generator, Execution Engine with the Self-Healing Engine, Failure Analyzer, Reporting Engine and Dashboard. A person stays in the loop: generated test cases are approved by a human before scripting (the demonstration shortcut `--approve-all` is stated wherever it is used), and a proposed locator repair becomes permanent only through `aitaf approve-heal`. The system runs end to end against a local demonstration shop with 37 seeded mutations, in a real Chromium, with the mock provider (offline, free) or a live OpenAI model (gpt-4o-mini). The suite has 1,381 tests, 94% line and branch coverage, CI green on Ubuntu and Windows, and a Docker image built and run end to end in CI.

**What the numbers say, in one paragraph (details in section 4):** healing repaired 32 of 37 seeded mutations, all correctly, with one false heal among ten absent-element controls; classification agreed with the author's labels on 66.0% of the first 50 failures and on 80.7% of 57 new hold-out failures after the rules were improved; generated scripts ran without a missing element or runtime error in 38.9% of cases (mock) and 33.3% (live) with page context, against a target of 80%, so **objective O2 is not met**; non-LLM latency was well inside its limit; live API cost for the whole Unit 6 evaluation was about $0.07.

## 2. Modules built and requirement coverage

"Done" means implemented, tested and exercised end to end on the demo shop. Totals over the 39 functional requirements: **36 done, 3 partly, 0 not built**.

| Component / package | Requirements | Status |
|---|---|---|
| Requirement Analyzer (`analyzer`) | FR-01 to FR-05 | Done (prompt `ra-v2`) |
| Test Case Generator (`generator`) | FR-06 to FR-11 | Done |
| Script Generator (`scriptgen`) | FR-12, FR-14, FR-15, FR-16 | Done; scripts run in Chromium; page context (`PageCatalogue`, prompt `sg-v2`) added in Unit 6 |
| | FR-13 (Selenium) | Partly: generated and validated, executed only with a fake driver |
| Execution Engine (`execution`) | FR-18, FR-19, FR-20, FR-21 | Done (screenshots, DOM snapshots, JUnit, retries, workers, time limit, host allow-list) |
| | FR-17 (Playwright and Selenium) | Partly: Playwright in a real browser, Selenium not |
| Self-Healing (`healing`, called by the engine) | FR-22 to FR-26 | Done; permanent update through `aitaf approve-heal` (closes the Unit 5 approval gap) |
| Failure Analyzer (`diagnosis`) | FR-27, FR-28, FR-29 | Done (ordered rules; model step only for unrecognised failures) |
| Reporting Engine (`reporting`) | FR-31, FR-32, FR-34, FR-39 | Done (HTML, Markdown, PDF through Chromium, metrics, traceability) |
| Dashboard (`dashboard`) | FR-33 | Partly: pass rate, healing, accuracy, coverage, executability, cost, latency and a trend over runs; **code coverage is not shown** |
| Evaluation harness (`evaluation`, `sampleapp`) | FR-38, FR-39 | Done (seeded mutations, hidden ground truth, corpora, scorers) |
| Cross-cutting (`core`, CLI) | FR-30, FR-35, FR-36, FR-37, FR-19 | Done; every stage plus `run`, `approve-heal`, `dashboard`, `evaluate` work |

Non-functional requirements shown by tests or evidence: NFR-01 (non-LLM latency), NFR-05 (clean-environment runs in CI and in the image), NFR-06 (retry with back-off for the live provider), NFR-07, NFR-08 (response cache), NFR-09 (key only from the environment), NFR-10, NFR-11, NFR-13, NFR-17 (automated import rules, zero violations), NFR-18 (coverage 94%), NFR-19 (lint and types in CI), NFR-20 (package READMEs), NFR-26 (Ubuntu and Windows in CI), NFR-29 (report and Dashboard are offline, summary first, text alternatives; a human review is still pending), NFR-30, NFR-31. Not shown: NFR-03 (healing overhead measured as decision time only, 1.4 ms p95, no browser time), NFR-23 (parallel scaling not measured), NFR-27 (install time not stopwatched).

## 3. Integration (Part A facts)

**A1 input and output.** `aitaf run --input data/requirements/shop_requirements.md --demo-shop --approve-all [--heal] [--mutation ID]` takes 20 plain-text requirements and produces, in order: 18 analysed requirements ready and 2 flagged as vague (by design), 54 test cases and scenarios, 54 Playwright scripts with 12 locators, results, healing events, failure analyses with clusters, an HTML and Markdown report, and the Dashboard. Evidence E10b holds the console logs of three consecutive runs and the full report of the third; E11b holds the Dashboard built from the three runs.

| Run (mock provider, demo shop) | Passed / failed | Pass rate | Healing success |
|---|---|---|---|
| 1 unmutated, no healing | 21 / 33 | 38.9% | n/a |
| 2 `M-add_backpack-id`, no healing | 21 / 33 | 38.9% | n/a |
| 3 `M-add_backpack-id`, `--heal` | 30 / 24 | 55.6% | 5.0% (1 of 20 steps) |

**Read this table carefully.** The mutation did not change the pass count because the scripts that pass do not depend on that element. The nine extra passes in run 3 come from **one** proposed repair (the locator for a "remove" button replaced by the shop's add button, confidence 0.65). The repair looks wrong (opposite action) and was not reviewed; a person using `aitaf approve-heal` would be expected to reject it. Report the table as a demonstration of the pipeline and the Dashboard, and report the repair as a finding, **not** as an improvement from healing. The 33 and 24 failures are almost all `locator` findings: the mock model writes plausible but generic steps that do not fit every page.

**A2 key code.** Line ranges to screenshot (at tag `v1.0.0-rc1`) are in `UNIT6_SCREENSHOT_GUIDE.md`.

**A3 inter-module communication (what talks to what).**
- Gateway call and audit: `core/llm/gateway.py` `complete()` (call cap, provider, fallback, audit record per call).
- Repository write and read: the engine stores each result with `add_result`; the Reporting Engine and the Dashboard read stored runs through the repository interface (`SqliteRepository`).
- Engine to healer: the engine knows only the `LocatorHealer` interface in `core/healing.py`; the command line injects the real healer (NFR-17).
- Stage chaining: `aitaf/pipeline.py` calls the same command line stages a person would type; the run IDs link requirement, test case, script, result, failure analysis and report (FR-34).
- Dashboard to Reporting Engine: `dashboard/data.py` calls `build_report`, so the Dashboard and the run report cannot disagree.

## 4. Evaluation facts (Part B)

Raw data and the generated tables are in `evaluation/results/` (`RESULTS.md`, CSV files, three charts). Every figure in `RESULTS.md` carries its numerator, denominator and basis. **Mock rows measure the pipeline and the rules, not a language model; live rows are labelled live and rest on one run of one small model.**

| Objective (target) | Measured | Verdict |
|---|---|---|
| O1 requirement coverage (at least 90% of 20 requirements with an approved case) | 90.0% (18 of 20; 2 flagged vague by design) | Met, exactly at the target |
| O2 script executability (at least 80%) | Mock without page context 0.0% (0/54); mock with page context 38.9% (21/54); live without context 0.0% (0/30); live with context 33.3% (8/24); locator validity with context 100% (12/12) | **Not met.** Page context fixed the locators; the remaining failures are steps that do not match the application's behaviour |
| O3 healing (at least 70% success, at most 5% false heals, 30 or more mutations) | 86.5% (32/37) success; all 32 correct; false-heal rate 2.1% (1/47 trials); id, class and structure 30/30; text rewordings 2/7 (the healer deliberately refuses a candidate whose visible text changed); 1 of 10 absent-element controls got a wrong repair (control rejection 90%) | Met; state the text-change recall and the control result |
| O4 classification (at least 75% on 40 or more labelled failures) | First 50 failures, rules v1: 66.0% (33/50). Rules v2 on the same 50: 88.0% (44/50), **tuned on those errors, not independent**. Hold-out 57 failures: v1 75.4% (43/57), v2 80.7% (46/57) | Met on the hold-out with v2; the honest figures are 66.0% (first) and 75.4% / 80.7% (independent) |
| O5 latency (non-LLM under 5 s for 95% of runs) | Report build and write: median 99.8 ms, p95 119.1 ms (29 samples, warm-up excluded); healing decision median 0.6 ms, p95 1.4 ms | Met |
| O6 quality (coverage at least 80%, CI green) | 94% line and branch; 1,373 tests run by default plus 8 real-browser tests; CI green | Met |

**Cost (live, gpt-4o-mini):** script generation evaluation $0.0312 (without page context) and $0.0338 (with); the two generation runs cost $0.065 together; with the smoke test and the analyzer checks the total live spend for Unit 6 was about $0.07 (the figure is rounded; the audit table holds the exact values). The mock provider costs nothing.

**Classification details worth quoting.** The rules misjudged 8 of 8 rejected-input failures as assertion defects, 4 of 8 timeouts as locator failures and an HTTP 404 assertion as a defect (v1). Rules v2 added a validation-message rule, made a raw timeout a timing failure and made a 4xx or 5xx status assertion an environment failure; they were scored on a **new** hold-out set labelled before the scoring. On the hold-out, locator recall fell to 75% because the two label sets disagree on raw "waiting for locator" timeouts (timing in the first set, locator in the second): treat that as a labelling-consistency limit, not a result to tune away.

**Live Requirement Analyzer.** With prompt `ra-v1` the live model flagged 17 of 18 clear requirements as ambiguous. Prompt `ra-v2` (an ambiguities rule; its example is unrelated to the shop requirements) gave 18 ready, 1 flagged and 1 rejected (model output invalid twice). It was tuned on the same 20 requirements, so this is a development-set result.

**B2 qualitative metric.** `evaluation/qualitative/RUBRIC.md` defines the rubric (clarity, completeness, actionability; five questions, 1 to 5, with comments). `ratings.csv` holds **five AI-assisted draft rows (reviewer `AI1`) that are not a human review** and must not be reported as the qualitative metric. The author (and, if available, up to two volunteer peers with consent) still has to rate the report (E11) and the Dashboard (E11b). Until then, state B2 as "method defined, review pending".

## 5. Deployment and configuration (Part C facts)

- **Methods compared** (full table in `docs/user-guide/DEPLOYMENT.md` section 1): local virtual environment, Docker image, GitHub Actions. **Choice:** develop locally, ship and demonstrate with Docker, let CI build the image and run the pipeline inside it. Cloud and on-premise hosting were considered and not built: the framework is a command-line tool, not a service.
- **Prerequisites:** Python 3.12, Git, Docker for the container method, network access, an OpenAI key only for live runs.
- **Configuration:** all settings come from the environment (or a JSON file, never the key): `LLM_PROVIDER` (mock by default), `OPENAI_API_KEY`, `LLM_MODEL`, `LLM_CALL_CAP`, `LLM_MAX_RETRIES`, `LLM_TIMEOUT_S`, `LLM_CACHE_DIR`, `LLM_PRICE_IN_PER_1K`, `LLM_PRICE_OUT_PER_1K`, `LOG_LEVEL`. `.env.example` is the template; `.env` is git-ignored; the key is never in the image, a file, a log or a prompt. Invalid values stop the run with exit code 2. A test keeps the guide and the code's settings in step.
- **Commands:** install `pip install -r requirements-dev.txt -r requirements-report.txt`, `python -m playwright install chromium`, `pip install -e . --no-deps`; image `docker build -t aitaf:local .`; run `docker run --rm --ipc=host -v "$(pwd)/reports:/app/reports" aitaf:local run --input data/requirements/shop_requirements.md --db reports/aitaf.db --out-dir reports/pipeline --demo-shop --approve-all`.
- **How configuration management supports reliability:** pinned dependencies (`requirements*.txt`), `Settings` validation, versioned prompts (`ra-v2`, `sg-v2`, `fa-v1`), CI on every push, tags with a version-to-tag check, a response cache for repeatable live runs (REF-022, Summers Ch. 8).
- **Verification:** the image was **not built on the author's machine**. CI built it and ran the whole pipeline in the container with the mock provider (Integration run #8, job "docker image", all steps green; E15 log). The local virtual-environment install is the method the author used daily.

## 6. Tests and coverage facts

- **1,381 tests: 845 black-box, 536 white-box.** 1,373 run by default; **8 real-browser tests** (marker `integration`) run in `integration.yml` (Chromium on Ubuntu, green). A share of the white-box count is documentation and import-rule checks, so the behaviour test count is lower than the headline.
- **Coverage 94%** (6,135 statements, 1,540 branches, gate 80%).
- **Techniques used in Unit 6:** a fake-browser project over real PyTest subprocesses, `pytester` for the plugin, real Chromium for the journey, hidden ground truth (oracle rendering) for healing, corpora scored only against labels written first, fault injection of invalid model output, a pipeline test with a fake stage runner, file-consistency tests for the deployment pack.
- **CI:** CI #47 (lint, types, import rules, tests on Ubuntu and Windows, security, build), Integration #8, Release #3, all on commit `86a6095`.

## 7. Evidence (the author checks every screenshot)

Register: `evidence/EVIDENCE_REGISTER.md`. Screenshots go in `evidence/unit06/screenshots/`. The full shot list, captions, line ranges and local pages are in `UNIT6_SCREENSHOT_GUIDE.md`; the evidence session follows `UNIT6_EVIDENCE_BRIEF.md`.

| ID | Shows | Where |
|---|---|---|
| E10 | Failure Analyzer output | `evidence/unit06/logs/` (U6-5 log) and `E10_pipeline/` |
| E10b | `aitaf run` three runs, report of run 3 | `evidence/unit06/E10_pipeline/` |
| E11, E11b | Report of a real-browser run; Dashboard of three runs | `evidence/unit06/E11_report/`, `E11_dashboard/` |
| E12 | Key code and inter-module excerpts | screenshots of GitHub pages (pending) |
| E13 | Metrics data and charts | `evaluation/results/` |
| E14 | Qualitative review | pending human ratings |
| E15 | Deployment files and CI proof | `Dockerfile`, `docs/user-guide/DEPLOYMENT.md`, `evidence/unit06/logs/E15_deployment_ci_20261116.txt` |
| E17c | Tag and release `v1.0.0-rc1` | `evidence/unit06/logs/E17c_tag_v1.0.0-rc1_20261116.txt`, release page |
| E04b, E09b | Live smoke test; healing in a real browser | `evidence/unit06/logs/` |

Label every generated output **mock** or **live** in its caption.

## 8. Real issues and challenges (the only ones that may be quoted)

Source: `PROGRESS_LOG.md` (sections "Issues found by tests" and "Challenges and resolutions"). Recommended selection for the documents: (1) classification v1 scored 66% and what the three error groups taught; (2) the improved classifier was scored on a new hold-out set instead of the set it was tuned on (ADR-043); (3) the Script Generator never saw the application, so executability could not be measured, which led to the page catalogue; (4) the pipeline failed inside the container because relative evidence paths pointed nowhere once pytest ran from the scripts folder; (5) the release guard refused the first `v1.0.0-rc1` tag because the version and changelog were not updated; (6) mypy failed in CI because the optional charts library and pandas stubs were missing there; (7) the live analyzer over-flagged ambiguity (prompt `ra-v2`); (8) the healed passes in the demonstration rest on one unreviewed repair. Do not add issues that are not in the log.

## 9. Reading map (course references first, ADR-020)

| Reference | Use it for |
|---|---|
| REF-020 LaunchNotes, REF-021 Helpjuice | Part C: deployment and release concepts, documentation for setup |
| REF-022 Guru99, REF-023 Sumo Logic | Part C: configuration management, deployment methods and environments |
| REF-024 LinearB | Part B and Part D: metrics and what to measure |
| REF-025 Bytebytego (video) | Part C: containers and deployment choice |
| Summers (2020), Chapter 8 | Parts B and C: integration, testing at system level, configuration management (confirm the chapter number) |

External sources in Chapter 5.2 follow the author's decision O-10. No invented references (ADR-009).

## 10. Do not claim

- That a language model's quality was measured in general: live figures are one run of gpt-4o-mini; most rows are mock.
- That script executability meets its target. It does not (38.9% mock, 33.3% live, target 80%). **Do not use the report's or the Dashboard's "script executability" figure (100%) for O2**: it counts a script as executable if its test passed or failed, so a missing locator counted as executable. Use the evaluation figure in `RESULTS.md`.
- That healing improved the pass rate: the nine extra passes in the demonstration rest on one unreviewed repair that looks wrong.
- A classification accuracy of 88.0% as independent: it was tuned on the same 50 failures. Independent figures are 66.0% (first rules, first 50), 75.4% and 80.7% (hold-out). The labels were written by the author alone.
- A qualitative score: the five `AI1` rows are an AI-assisted draft, not a review.
- That the Docker image was built or run on the author's machine; only CI did.
- That Selenium runs in a real browser, or that the Dashboard shows code coverage.
- That the demo shop is a production application; it is a local demonstration with open login and 37 seeded mutations.
- That `main` contains this work: it is on `develop` until submission.
- Any legal, privacy or compliance conclusion (GDPR wording needs the Data Privacy Officer).

## 11. Author to-do before submission

1. Take or check the screenshots in `UNIT6_SCREENSHOT_GUIDE.md` (sign-in-only GitHub pages in a private window, no bookmarks bar).
2. Complete the qualitative review (E14) with a human reviewer; decide O-14 (peers) and O-10 (external sources) and O-16 (due dates).
3. Commit `.env.example` (renamed from `.env.example.md`) after checking it holds no real key.
4. Run Cowork with the two prompts at the end of `UNIT6_SCREENSHOT_GUIDE.md`, then review both documents yourself (ADR-009).
5. Optional: install Docker and run `docker build` and the demo command locally for a first-hand capture.
