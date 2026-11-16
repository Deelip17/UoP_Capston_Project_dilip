# Unit 6: screenshot guide, assignment coverage and Cowork prompts

Companion to `UNIT6_HANDOFF.md` (facts, issues, do-not-claim list). This file says **what to capture and how**, shows that **every task of the assignment is covered**, and holds the **two prompts for Cowork**. The evidence session that takes the screenshots follows `UNIT6_EVIDENCE_BRIEF.md`.

Base address: `https://github.com/Deelip17/UoP_Capston_Project_dilip` (public). Code is shown at tag **v1.0.0-rc1** so line numbers stay fixed (ranges are approximate: scroll so the highlighted block is visible); logs and evidence are shown on **develop**. Local pages are opened from the repository folder with a `file://` address.

## 1. Set up once (5 minutes)

1. Use a **private or incognito window** (Edge or Chrome): it hides your avatar and bookmarks and shows the repository is public.
2. Zoom 110 to 125%, window at least 1,400 px wide, **light** theme.
3. Screenshot tool: **Win + Shift + S**, save as PNG into **`evidence\unit06\screenshots\`** with the file names below.
4. Include the **address bar** in GitHub shots. Crop everything else (no bookmarks bar, no user name, no local path). Keep each image to about 45 code lines.
5. **Sign-in-only pages** (GitHub Actions job logs) must be captured by you in the private window while signed in; the run summary page works signed out.
6. Label every output **mock** or **live** in its caption.

## 2. Shot list ("Doc 1" = Parts A to C, "Doc 2" = Part D)

### Part A: integration, input and output (A1)

| # | File name | How | Caption (suggested) | Use |
|---|---|---|---|---|
| 1 | `E10b_run_console.png` | `.../blob/develop/evidence/unit06/E10_pipeline/run3_console.txt`, top of the file | Figure 1. `aitaf run` on the demo shop: requirements in, analysis and test cases out (mock provider) | Doc 1 |
| 2 | `E10b_run_stages.png` | same file, scroll to the `== execute`, `== diagnose` and `== report` headings | Figure 2. The same run: execution with healing, failure analysis and metrics (mock) | Doc 1 |
| 3 | `E11_report_top.png` | local `evidence/unit06/E10_pipeline/run3_report/report.html`, top of the page | Figure 3. Run report: summary first, metrics with their basis (mock) | Doc 1 |
| 4 | `E11_report_failure.png` | same page, one failure with category, confidence, cause, next step and screenshot | Figure 4. A failure explained: category, confidence, cause, next step, evidence links | Doc 1 |
| 5 | `E11b_dashboard_top.png` | local `evidence/unit06/E11_dashboard/dashboard.html`, top (latest-run tiles) | Figure 5. Dashboard: latest run first (mock) | Doc 1 |
| 6 | `E11b_dashboard_trend.png` | same page, the chart section and the run table | Figure 6. Dashboard: trend over three stored runs and the table behind it (mock) | Doc 1 |
| 7 | `E10_login_page.png` | optional: the demo shop login page (`aitaf.sampleapp`, run `python -m aitaf.sampleapp serve`) | Optional: the system under test | Optional |

### Part A: key code (A2) and inter-module communication (A3), file `E12_*.png`

All at `.../blob/v1.0.0-rc1/<path>#L<start>-L<end>`. Each figure gets a one-sentence explanation in the text.

| # | File name | Path and lines | What it shows | Use |
|---|---|---|---|---|
| 8 | `E12_engine_loop.png` | `src/aitaf/execution/runner.py#L267-L293` | Execution Engine: run, collect failures, offer them to the healer, rerun, retry | Doc 1 |
| 9 | `E12_engine_heal.png` | `src/aitaf/execution/runner.py#L337-L383` | Healing integration: one question per locator, heal on a temporary copy | Doc 1 |
| 10 | `E12_failure_rules.png` | `src/aitaf/diagnosis/rules.py#L143-L195` | Failure Analyzer: ordered rules (assertion before locator) | Doc 1 |
| 11 | `E12_report_metrics.png` | `src/aitaf/reporting/metrics.py#L75-L110` | Reporting Engine: metrics computed from stored data, None instead of zero | Doc 1 |
| 12 | `E12_dashboard_collect.png` | `src/aitaf/dashboard/data.py#L49-L81` | Dashboard: one row per stored run, built with the report's own function | Doc 1 |
| 13 | `E12_eval_harness.png` | `src/aitaf/evaluation/classify_eval.py#L88-L139` | Evaluation harness: classifier scored only against labels written first | Doc 1 |
| 14 | `E12_gateway_call.png` | `src/aitaf/core/llm/gateway.py#L56-L79` | A3: gateway call with call cap, provider, fallback and audit record | Doc 1 |
| 15 | `E12_repo_write_read.png` | `src/aitaf/core/storage/sqlite.py#L240-L268` | A3: repository write and read of results (SQLite) | Doc 1 |
| 16 | `E12_healer_interface.png` | `src/aitaf/core/healing.py#L46-L75` | A3: the interface between engine and healer (`LocatorHealer`) | Doc 1 |
| 17 | `E12_pipeline.png` | `src/aitaf/pipeline.py#L71-L110` | A3: `aitaf run` chains the stages and keeps the human gate | Doc 1 |
| 18 | `E12_approve_heal.png` | `src/aitaf/healing/approval.py#L25-L69` | Approval gate: a repair becomes permanent only after approval | Optional |
| 19 | `E12_scriptgen_catalogue.png` | `src/aitaf/scriptgen/catalogue.py#L139-L155` | Page context: a plan may use only elements that exist on the page | Optional |

If Doc 1 cannot hold all of A2 and A3, keep figures 8, 9, 10, 11, 12, 14, 15 and 17 and leave the rest in the evidence folder.

### Part B: evaluation (B1, B2, B3)

| # | File name | How | Caption (suggested) | Use |
|---|---|---|---|---|
| 20 | `E13_results_healing.png` | `.../blob/develop/evaluation/results/RESULTS.md`, healing table | Figure: healing results over 37 seeded mutations (86.5% success, 2.1% false heals) | Doc 1 |
| 21 | `E13_results_classification.png` | same file, classification tables (first 50 and hold-out 57) | Figure: classification against the author's labels, development set and hold-out | Doc 1 |
| 22 | `E13_results_generation.png` | same file, generation tables (mock and live) | Figure: script executability with and without page context | Doc 1 |
| 23 | `E13_chart_healing.png` | `.../blob/develop/evaluation/results/charts/healing_by_kind.png` | Chart: healing repairs by mutation kind | Doc 1 |
| 24 | `E13_chart_classification.png` | `.../charts/classification.png` | Chart: classification accuracy by rules version and set | Doc 1 |
| 25 | `E13_chart_generation.png` | `.../charts/generation.png` | Chart: script executability by configuration | Doc 1 |
| 26 | `E13_raw_csv.png` | `.../blob/develop/evaluation/results/healing.csv` | Optional: raw data behind the table | Optional |
| 27 | `E14_qualitative_sheet.png` | `.../blob/develop/evaluation/qualitative/ratings.csv` **after** the human review (see handoff section 4) | Qualitative review: rubric scores with comments | Doc 1 (when done) |
| 28 | `E14_rubric.png` | `.../blob/develop/evaluation/qualitative/RUBRIC.md` | The rubric used | Optional |

### Part C: deployment and configuration (C1, C2, C3)

| # | File name | How | Caption (suggested) | Use |
|---|---|---|---|---|
| 29 | `E15_dockerfile.png` | `.../blob/v1.0.0-rc1/Dockerfile` | Figure: the container definition (non-root user, no secret, mock provider by default) | Doc 1 |
| 30 | `E15_deployment_guide.png` and `E15_deployment_guide_s3.png` | `.../blob/v1.0.0-rc1/docs/user-guide/DEPLOYMENT.md`: section 1 (methods) in the first image, section 3 (variables) in the second | Figure: deployment methods compared and the settings table | Doc 1 |
| 31 | `E15_env_example.png` | `.../blob/develop/.env.example` (after you commit it) | Figure: configuration template, no secret values | Doc 1 |
| 32 | `E15_ci_integration.png` | `.../actions/runs/43800603134` (Integration #8) summary page, both jobs green | Figure: CI builds the image and runs the pipeline inside it | Doc 1 |
| 33 | `E15_ci_docker_job.png` | same run, job "docker image (build and demo run)", the step list (**sign in, private window**) | Figure: build, command check and in-container pipeline run | Doc 1 |
| 34 | `E15_install_terminal.png` | VS Code terminal: `pip install -r requirements-dev.txt -r requirements-report.txt` then `aitaf --help` | Figure: install and first command | Optional |

### Release candidate (supports Parts C and D)

| # | File name | How | Caption (suggested) | Use |
|---|---|---|---|---|
| 35 | `E17c_release_rc1.png` | `.../releases/tag/v1.0.0-rc1`, notes and both assets visible | Figure: release candidate v1.0.0-rc1 with the wheel and the evidence bundle | Doc 1 or 2 |
| 36 | `E17c_tags.png` | `.../tags` | Figure: annotated tags v0.1.0, v0.5.0 and v1.0.0-rc1 | Optional |
| 37 | `E07_ci_summary.png` | `.../actions/runs/43800603157` (CI #47), all jobs green | Figure: continuous integration on the release-candidate commit | Doc 2 |
| 38 | `E07_coverage.png` | terminal: `pytest --cov=aitaf` last lines (94%, 1,373 passed) | Figure: tests and coverage | Optional |
| 39 | `E17_repo_home.png` | `.../` signed out, "Public" visible | Figure: public repository | Optional (shown in Unit 5) |

## 3. Assignment coverage

| Task | Content comes from | Figures | Status |
|---|---|---|---|
| **A1** input-output examples of the integrated system | Handoff section 3 (the three-run table, with its caveat), E10b, E11, E11b | 1 to 6 | Needs screenshots |
| **A2** key code of the main modules with a short explanation | Handoff sections 2 and 3; figures 8 to 13 | 8 to 13 (18, 19 optional) | Needs screenshots |
| **A3** inter-module communication (API requests, database, UI-backend) | Handoff section 3 (A3 list); figures 14 to 17 | 14 to 17 | Needs screenshots |
| **B1** at least two quantitative metrics with screenshots | Handoff section 4; `RESULTS.md`; healing, classification, generation, latency, coverage, cost | 20 to 22 | Needs screenshots |
| **B2** at least one qualitative metric with screenshots | Rubric and rating sheet (E14). **Your self-review (R1 rows) still to do**; the `AI1` draft rows are not part of the result | 27 | **Blocked on you** |
| **B3** results table, chart and interpretation | Handoff section 4 table (measured against target), charts 23 to 25; 3 to 5 sentences each, honest about O2 not met and the tuned rules | 23 to 25 | Needs screenshots |
| **C1** deployment methods and the choice | `DEPLOYMENT.md` section 1; handoff section 5; REF-023, REF-025 | 30 | Ready |
| **C2** configuration management | Handoff section 5; `Settings`, `.env.example`, pinned requirements, CI, tags; REF-022 and Summers Ch. 8 | 29, 31, 35 | Ready |
| **C3** prerequisites, variables, install, build and deployment commands | `DEPLOYMENT.md` sections 2 to 5; CI proof (E15) | 29 to 34 | Ready (Docker verified by CI only) |
| **D** Chapters 4 to 6 (results, discussion, conclusion) | Everything above plus the Unit 4 and 5 handoffs; limits from the do-not-claim list | all | Cowork |
| Sources and course connection | Reading map in the handoff | none | Cowork |

## 4. Alignment with the project objectives (for A1, B3 and Part D; state only what holds)

| Objective | Measured result | Target met? |
|---|---|---|
| O1 requirement coverage | 90.0% (18 of 20) | Yes, at the target |
| O2 script executability | 38.9% mock, 33.3% live with page context (0% without) | **No** (target 80%) |
| O3 healing | 86.5% success, 2.1% false-heal rate; text rewordings 2/7; 1 of 10 controls wrongly repaired | Yes |
| O4 classification | 66.0% first (50), 75.4% and 80.7% hold-out (57); labels by the author alone | Yes on the hold-out; first run below target |
| O5 latency | p95 119 ms (non-LLM) | Yes |
| O6 quality | 94% coverage, CI green | Yes |
| O7, O8 | Not re-measured in Unit 6 beyond the controls already tested (allow-list, secret-free environment, masking, approval gates) | Not claimed |

## 5. Prompts for Cowork

Give Cowork access to the repository folder and to the workspace folder. If it cannot see the repository, copy `docs/project-management/`, `evidence/` and `evaluation/` into the workspace first. Run the prompts **one at a time**.

### Prompt 1: document 1 (Parts A to C)

```text
Written for: Cowork, preparing the Unit 6 assignment document 1 (Parts A to C) for the MSIT Capstone.

Task: write document 1 as a Word document, using only the sources below.

Read first (in this order):
1. 01_UNIT_INSTRUCTIONS/Unit06_Integration_Feature_Completion_Evaluation.md (assignment and rubric)
2. docs/project-management/UNIT6_HANDOFF.md in the repository (facts, results, issues, do-not-claim list, reading map)
3. docs/project-management/UNIT6_SCREENSHOT_GUIDE.md: section 2 (figure list and captions), section 3 (assignment coverage), section 4 (objectives)
4. docs/project-management/PROGRESS_LOG.md (the only source of issues and challenges)
5. evidence/EVIDENCE_REGISTER.md and the images in evidence/unit06/screenshots/ (match them by file name to the guide); evaluation/results/RESULTS.md and the CSV files for numbers; docs/user-guide/DEPLOYMENT.md for Part C
6. knowledge/RESEARCH_FRAME.md section 4 (objectives O1 to O8)
7. reference-library/MASTER_REFERENCES.md entries REF-020 to REF-025 and Summers (2020) Chapter 8 (the only references to cite; APA 7; no new and no invented references)

Structure and format:
- Total 1,300 to 1,450 words excluding references and title (the instruction file allows up to 1,500); double-spaced Times New Roman 12 pt; screenshots inside the document as numbered figures with the captions from the guide, each labelled mock or live.
- Sections in this order: A1, A2, A3, B1, B2, B3, C1, C2, C3, using the headings of the assignment. Suggested budget: Part A 500, Part B 500, Part C 400 words.
- A1: the three-run example with the caveat stated in the handoff (the extra passes rest on one unreviewed repair). A2: one sentence per code figure. A3: the five communication paths listed in the handoff.
- B1: at least two quantitative metrics with their numerators and denominators (healing, classification, generation, latency, coverage; cost). B2: report the qualitative metric as a **self-review by the author** (reviewer R1) of the report and the Dashboard, using only the rows with reviewer code R1 in evaluation/qualitative/ratings.csv: the method from RUBRIC.md, the median and range per question, one reviewer, and the limit that the reviewer is also the author. Ignore every row with reviewer code AI1 (an AI-assisted draft, not part of the result). If there are no R1 rows yet, write 'the self-review is pending' and insert a visible placeholder; never invent scores. B3: the measured-versus-target table from section 4 of the guide, two charts, and 3 to 5 sentences of interpretation each, including that O2 is not met and that the 88.0% classification figure is not independent.
- C1 to C3: the comparison of methods and the choice from DEPLOYMENT.md, configuration management, prerequisites, variables, install, build and deployment commands. State that the Docker image was built and run by CI, not on the author's machine.

Rules:
- Quote only issues and challenges that appear in PROGRESS_LOG.md. Do not invent results, numbers, quotes or references.
- Follow the "Do not claim" list in the handoff exactly (in particular: do not use the report's or Dashboard's "script executability" figure for O2; do not present healing as improving the pass rate; do not use the AI1 rows; the qualitative result is the author's R1 self-review only).
- First person singular, academic tone, past tense for what was built. Mark anything you are unsure about instead of guessing.

Deliver: the .docx, then a short report with (a) word count per part and total, (b) a checklist showing where A1 to C3 are covered, (c) figures used and any missing (use a visible placeholder "[Figure n: expected file name]" for a missing image), (d) any statement you could not support from the sources. I will review and edit the document myself before submitting.
```

### Prompt 2: document 2 (Part D, Chapters 4 to 6)

```text
Written for: Cowork, preparing the Unit 6 assignment document 2 (Part D: Chapters 4, 5 and 6 of the Capstone template) for the MSIT Capstone.

Task: write Chapters 4, 5 and 6 as a Word document, using only the sources below. Also write **Author notes** as a separate short page after the document (not part of the word count): what you assumed, every statement or number you want me to verify, anything you could not support from the sources, decisions still open (O-10, O-14, O-16), and what I must check before submitting.

Read first (in this order):
1. 01_UNIT_INSTRUCTIONS/Unit06_Integration_Feature_Completion_Evaluation.md (Part D and the rubric) and the Capstone report template in the workspace (use its chapter and section numbering and headings)
2. docs/project-management/UNIT6_HANDOFF.md (all sections, especially the results, the do-not-claim list and the reading map), docs/project-management/UNIT5_HANDOFF.md and the Unit 4 handoff for earlier facts
3. docs/project-management/UNIT6_SCREENSHOT_GUIDE.md sections 3 and 4 (coverage and objectives)
4. docs/project-management/PROGRESS_LOG.md (the only source of issues and challenges), evaluation/results/RESULTS.md and the CSV files, evaluation/LABELLING_GUIDE.md
5. knowledge/PROJECT_DECISIONS.md (ADR-042, ADR-043 on evaluation integrity), knowledge/RESEARCH_FRAME.md section 4, the Chapters 1 to 3 notes in final-report/ if present
6. evidence/EVIDENCE_REGISTER.md, the images in evidence/unit06/screenshots/ and evaluation/qualitative/ratings.csv with RUBRIC.md (use only rows with reviewer code R1; ignore AI1 rows)
7. reference-library/MASTER_REFERENCES.md: REF-020 to REF-025, Summers (2020) Chapter 8, and earlier-unit sources only as allowed by the author's decision O-10 (if O-10 is not recorded, use course readings only and say so)

Structure and format:
- 5,200 to 5,800 words (the instruction file allows 4,500 to 6,000), with the template's numbering. Chapter 4 (implementation and results): the integrated system, the evaluation design, the results per objective O1 to O8 with tables and charts. Chapter 5 (discussion): what the results mean, what worked and what did not (O2 not met and why; healing and its false heals; classification and the labelling-consistency limit; the hold-out design), threats to validity (one demo application, one author labelling, one live run of one small model, mock rows measure the pipeline), comparison with the course readings. Chapter 6 (conclusion and future work): contributions, limitations from the do-not-claim list, future work (more applications, independent labellers, Selenium in a real browser, Dashboard code coverage, a larger live evaluation).
- Report the qualitative metric (objective evidence for report and Dashboard readability) as the author's **self-review** (reviewer R1): state that there is one reviewer who is also the author and what that means for validity in the threats to validity section. If there are no R1 rows yet, say it is pending and list it in the Author notes.
- Figures and tables: reuse the figures of document 1 where useful, with captions that say mock or live.

Rules:
- State measured values only as given in RESULTS.md and the handoff, with their denominators; keep independent and tuned results apart (66.0% first rules; 88.0% tuned on the same 50, not independent; 75.4% and 80.7% hold-out).
- Quote only issues and challenges from PROGRESS_LOG.md. Do not invent results, references or quotes; no legal, privacy or compliance conclusions (refer to the Data Privacy Officer).
- Do not claim anything on the do-not-claim list. First person singular, academic tone. Mark anything you are unsure about.

Deliver: the .docx, then (a) word count per chapter and total, (b) a checklist of objectives O1 to O8 and where each is discussed, (c) figures used and any missing, (d) any statement you could not support from the sources, (e) the Author notes page. I will review and edit the document myself before submitting (ADR-009).
```

## 6. Before you submit

1. All "Doc 1" screenshots exist in `evidence/unit06/screenshots/`, are readable at Word page width and have no bookmarks, user name or local path. Check every image yourself.
2. Each figure has a caption, is referred to in the text, and generated outputs say mock or live.
3. Do the qualitative self-review yourself (reviewer code R1, 15 minutes, your own scores and comments) and delete the `AI1` draft rows before B2 is written.
4. Commit `.env.example`; make sure the screenshot of it shows no real key.
5. Read both documents against the "Do not claim" list in the handoff; you are responsible for the content (ADR-009). Fill the title pages and check the word counts.
