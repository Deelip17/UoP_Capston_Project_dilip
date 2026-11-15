# Unit 5: screenshot guide, assignment coverage and Cowork prompt

Companion to `UNIT5_HANDOFF.md` (facts, issues, do-not-claim list). This file tells the author **how to capture each screenshot (GitHub web first)**, shows that **every assignment task is covered**, and holds the **prompt to give Cowork**.

Base address used below: `https://github.com/Deelip17/UoP_Capston_Project_dilip` (public). Code is shown at tag **v0.5.0** so line numbers stay fixed; evidence logs are shown on **develop**.

## 1. Set up once (5 minutes)

1. Open a **private or incognito browser window** (Edge or Chrome). It hides your avatar and notifications, and it proves the repository is public to someone who is not signed in.
2. Set browser zoom to **110 to 125%** and keep the window wide (at least 1,400 px). Use the **light** theme; it prints better.
3. Screenshot tool: **Win + Shift + S**, drag over the area, click the pop-up notification, **Save as** PNG. For a long page use the browser: Edge `Ctrl + Shift + S` then "Capture full page"; Chrome `F12`, `Ctrl + Shift + P`, type "Capture full size screenshot".
4. Save every file in the **`evidence\unit05\screenshots\`** folder inside the repository folder (`UoP_Capston_Project_dilip`), with the file name in the tables below (they start with the evidence ID).
5. Include the **address bar** in GitHub screenshots (it proves the source and shows the repository name). Crop away anything else. Keep each image to about 45 code lines at most so it stays readable on a Word page.
6. When finished, tell Claude Code "register the screenshots" (it adds them to `evidence/EVIDENCE_REGISTER.md` and commits), or add the rows yourself.

## 2. Shot list

"Paper" = recommended for the paper. Mark every output caption **(mock provider)**.

### Part A: code and output (6 required, 1 optional)

| # | File name | Open this address, then | Caption (suggested) | Paper |
|---|---|---|---|---|
| 1 | `E04_analyzer_code.png` | `.../blob/v0.5.0/src/aitaf/analyzer/analyzer.py#L137-L164` (lines turn yellow) | Figure 1. Requirement Analyzer: stable ID, combined rule and model risk rating, ambiguity flags (FR-02 to FR-05) | Yes |
| 2 | `E04_analyzer_output.png` | `.../blob/develop/evidence/unit05/logs/E04_analyzer_run_20261114.txt` | Figure 2. Analyzer output on the sample requirements (mock provider): 4 ready, 3 flagged, injected requirement rejected | Yes |
| 3 | `E06_validator_code.png` | `.../blob/v0.5.0/src/aitaf/scriptgen/validator.py#L113-L149` | Figure 3. Static validation of generated scripts by AST allow-list (FR-15, NFR-11) | Yes |
| 4 | `E06_script_output.png` | `.../blob/develop/evidence/unit05/logs/E06_script_generation_20261114.txt` | Figure 4. Script generation and rejection of forbidden constructs with reasons (mock provider) | Yes |
| 5 | `E09_similarity_code.png` | `.../blob/v0.5.0/src/aitaf/healing/similarity.py#L69-L85` | Figure 5. DOM-similarity scoring for self-healing (FR-23) | Yes |
| 6 | `E09_healing_output.png` | `.../blob/develop/evidence/unit05/logs/E09_self_healing_20261114.txt` | Figure 6. Self-healing scenarios on DOM fixtures, including a wrong element rejected and a defect left alone | Yes |
| 7 | `E05_testcases_export.png` | `.../blob/develop/evidence/unit05/E05_exports/test_cases.md` (GitHub renders it) | Optional figure: generated test cases linked to requirement IDs (FR-07, FR-34) | Optional |

Optional second code view for healing: `.../blob/v0.5.0/src/aitaf/healing/engine.py#L99-L137` (the repair ladder), file `E09_engine_code.png`.

### Part B: tests (4 required, 2 optional)

| # | File name | Open this address, then | Caption (suggested) | Paper |
|---|---|---|---|---|
| 8 | `E07_ci_summary.png` | `.../actions/runs/43672019877` (CI run 16). Show the green job list and the Summary tables | Figure 7. Continuous integration: all jobs green on Ubuntu and Windows (616 tests) | Yes |
| 9 | `E07_ci_pytest_log.png` | Same run, click **test (ubuntu-latest)**, expand **Unit tests with coverage**, scroll to the end | Figure 8. PyTest result and coverage table from the CI log: 616 passed, 97.86% coverage | Yes |
| 10 | `E07_blackbox_whitebox_code.png` | `.../blob/v0.5.0/tests/unit/healing/test_engine.py#L218-L244` (black-box example) and, in a second capture merged side by side or below, `#L434-L453` (white-box example) | Figure 9. A black-box test (public behaviour from the acceptance criterion) and a white-box test (internal branch) | Yes |
| 11 | `E08_coverage_html.png` | In File Explorer open `reports\htmlcov\index.html` in the repository folder (double-click; it opens in the browser; refreshed on 15 Nov, regenerate with `pytest --cov=aitaf --cov-report=html:reports/htmlcov`). Show the table with the total | Figure 10. Coverage report: 97.86% overall, healing modules 93 to 100% | Yes |
| 12 | `E07_labelled_tests_log.png` | `.../blob/develop/evidence/unit05/logs/E07_pytest_final_20261114.txt`, press `End` to show the last lines (coverage, 616 passed, "Tests by type") | Optional: tests labelled black-box and white-box (391 and 225) | Optional |
| 13 | `E07_issues_table.png` | `.../blob/develop/docs/project-management/PROGRESS_LOG.md#issues-found-by-tests-part-b` | Optional: issues found by tests and their fixes | Optional |

Also show the marker definitions once (can be merged into figure 9 or its own image): `.../blob/v0.5.0/pyproject.toml#L22-L29`, file `E07_markers_config.png`.

### Part C: version control (4 required, 3 optional)

| # | File name | Open this address, then | Caption (suggested) | Paper |
|---|---|---|---|---|
| 14 | `E17_repo_home.png` | `.../` (repository home, signed out). Show the **Public** label and the name | Figure 11. Public repository (link in the text) | Yes |
| 15 | `E17_branches.png` | `.../branches` | Figure 12. Branches: `main`, `develop` and the short-lived work branches | Yes |
| 16 | `E17a_tags.png` | `.../tags` | Figure 13. Annotated tags `v0.1.0` and `v0.5.0` | Yes |
| 17 | `E17b_release_v0.5.0.png` | `.../releases/tag/v0.5.0`, scroll so the notes **and** the two assets (wheel, evidence zip) are visible | Figure 14. GitHub Release v0.5.0 with release notes, wheel and evidence bundle | Yes |
| 18 | `E17_compare_tags.png` | `.../compare/v0.1.0...v0.5.0` | Optional: what changed between the two milestones | Optional |
| 19 | `E17_commit_history.png` | `.../commits/develop` | Optional: Conventional Commit history citing FR/NFR IDs | Optional |
| 20 | `E17b_release_workflow.png` | `.../actions/runs/43670876225` (the Release run: verify and release jobs green) | Optional: release automation | Optional |

If the paper cannot hold every "Yes" item, ask Cowork to keep the code and output pairs of the three strongest modules and all of Part C figures 11 to 14, and leave the rest in the evidence folder.

### If you also want a live terminal capture (optional, 2 minutes)

Open the repository folder in VS Code, open a terminal, activate the environment (`.venv\Scripts\activate`) and run one command, enlarging the font first (`Ctrl` and `+`):

```
python -m aitaf analyze --input data/requirements/sample_requirements.md --db demo.db
python -m pytest -q
python -m aitaf heal --before data/dom/login_before.html --after data/dom/login_all_changed.html --primary id=login-button --fallback "css=button[type=submit]"
```

Delete `demo.db` afterwards (it is git-ignored). Save as `E04_terminal.png`, `E07_terminal.png`, `E09_terminal.png`.

## 3. Assignment coverage

Every task of the assignment, where its content comes from, and which figures support it.

| Task | Content comes from | Figures | Status |
|---|---|---|---|
| **A1** How the implementation aligns with the project's main objectives | Handoff sections 1 and 2; objectives O1 to O8 in `knowledge/RESEARCH_FRAME.md` section 4 (see table in section 4 below) | none | Ready |
| **A2** Screenshots of essential code with their outputs | Figures 1 to 6 (optional 7) | 1 to 6 | Needs your screenshots |
| **A3** Challenges and how they were resolved | `PROGRESS_LOG.md` Challenges table; handoff section 5 (recommended four) | none | Ready |
| **B1** Screenshots or logs of successful test runs, and the type of testing | Figures 7 to 10; handoff section 3 (black-box and white-box definitions, 391 and 225); log `E07_pytest_final` | 7 to 10 | Needs your screenshots; type stated in text |
| **B2** Issues found by tests and how they informed improvements | `PROGRESS_LOG.md` Issues table (5 rows); handoff section 5 | optional 13 | Ready |
| **B3** Types of unit tests and how unit testing improves reliability and modular development | Course references REF-018 (isolation, mocks and stubs) and REF-006 (verification and validation); project examples: fake repository and mock provider (modularity), kill-process durability test, fault injection, 97.86% coverage gate | none | Ready (author's reading needed) |
| **C1** Tags and releases for major milestones | Figures 13, 14 (optional 18, 20); handoff section 6: `v0.1.0` initial development (core, persistence, gateway, Analyzer), `v0.5.0` core complete with tests and release automation; `v1.0.0` planned for the final release | 13, 14 | Needs your screenshots |
| **C2** Repository link with public access | `https://github.com/Deelip17/UoP_Capston_Project_dilip` (public); figure 11 | 11 | Needs your screenshot |
| **C3** Branching model, and how tags and releases help monitoring | `docs/project-management/GIT_STRATEGY.md` (model), handoff section 6 (actual practice: `develop` as working branch, ADR-028; tags on `develop`, ADR-033); REF-019; honest note that `main` is behind `develop` until submission | 12 (optional 19) | Needs your screenshots |

## 4. Alignment with the project objectives (for A1; state only what holds)

| Objective | What Unit 5 delivers | What is **not** yet shown |
|---|---|---|
| O1 traceable test cases | Requirement Analyzer and Test Case Generator, IDs linking requirement to case, review gate | The 90% coverage target on 20 requirements (the sample has 7) |
| O2 runnable scripts | Script Generator with validation, locator repository, Playwright and Selenium templates | Executability rate: scripts were never run in a browser |
| O3 locator repair | Self-Healing core on DOM fixtures, validation against wrong elements, approval gate | 70% success and 5% false-heal rates over 30 seeded mutations (Unit 6) |
| O6 code quality | Measured: 97.86% coverage (target 80%), CI green on `develop` | none |
| O8 security controls | Implemented with tests: masking, injection screening, schema validation of model output, AST allow-list, host allow-list, key only from the environment, two approval gates | Control status table is Unit 6 or 7 |
| O4, O5, O7 | Not addressed in Unit 5 (metrics hooks exist) | Measured in Unit 6 |

## 5. Prompt to give Cowork

Give Cowork access to the repository folder (`UoP_Capston_Project_dilip`) and to the workspace folder. If it cannot see the repository, copy `docs/project-management/` and `evidence/` from the repository into the workspace first. Then paste:

```text
Written for: Cowork, preparing the Unit 5 assignment document for the MSIT Capstone.

Task: write the Unit 5 assignment (Core Algorithm Implementation) as a Word document, using only the sources listed below.

Read first (in this order):
1. 01_UNIT_INSTRUCTIONS/Unit05_Core_Algorithm_Implementation.md (the assignment and rubric)
2. docs/project-management/UNIT5_HANDOFF.md in the repository (facts, issues, do-not-claim list, word budget, reading map)
3. docs/project-management/UNIT5_SCREENSHOT_GUIDE.md section 3 (assignment coverage), section 4 (objectives alignment) and the figure captions in section 2
4. docs/project-management/PROGRESS_LOG.md (the only source of issues and challenges)
5. evidence/EVIDENCE_REGISTER.md and the images in evidence/unit05/screenshots/ (use the file names to match figures to the captions in the guide); the text logs in evidence/unit05/logs/ if an image is missing
6. knowledge/RESEARCH_FRAME.md section 4 (objectives O1 to O8), docs/project-management/GIT_STRATEGY.md (branching model), knowledge/CURRENT_UNIT.md
7. reference-library/MASTER_REFERENCES.md entries REF-006, REF-017, REF-018, REF-019 (the only references to cite; APA 7; no new references, no invented ones)

Structure and format:
- Part A (about 550 words), Part B (about 500), Part C (about 350); total 1,400 to 1,500 words excluding references and title.
- Double-spaced Times New Roman 12 pt. Screenshots go inside the document as numbered figures with the captions from the guide (and "(mock provider)" on every generated output). Use the real PNG files; where a file is missing insert a visible placeholder "[Figure n: expected file name]" and list it in your final report.
- Cover every sub-task A1, A2, A3, B1, B2, B3, C1, C2, C3 of the assignment, in that order, with the headings used in the assignment. Part A must align the implementation with the objectives using the table in section 4 of the guide, and must say what is not yet measured.
- Part B must state the testing types performed (black-box and white-box, with the counts from the handoff), summarise the issues from the log and what each changed, and explain unit-test types and reliability and modularity with REF-018 and REF-006.
- Part C must give the repository link, the tags v0.1.0 and v0.5.0 with the release link, the branching model actually used (develop as working branch, main updated at submission) and how tags and releases support monitoring (REF-019). Say plainly that v0.1.0 is a tag without a release page, and that main does not yet contain this work.

Rules:
- Quote only issues and challenges that appear in PROGRESS_LOG.md. Do not invent results, numbers, quotes or references.
- Follow the "Do not claim" list in the handoff exactly (no live model output, no real-browser execution, no healing success rate, and so on).
- Write in first person singular, academic tone, past tense for what was built.
- Mark anything you are unsure about instead of guessing.

Deliver: the .docx, then a short report with (a) word count per part and total, (b) a checklist showing where each of A1 to C3 is covered, (c) the list of figures used and any missing, (d) any statement you could not support from the sources. I will review and edit the document myself before submitting.
```

## 6. Before you submit

1. All "Yes" screenshots exist in `evidence/unit05/screenshots/` and are readable at Word page width.
2. Each figure has a caption, is referred to in the text, and generated outputs say mock.
3. Read the paper against the "Do not claim" list in the handoff; you are responsible for the content (ADR-009).
4. Fill the title page; check the word count (1,400 to 1,500, excluding references and title).
5. Optional: create a release page for `v0.1.0` by hand (GitHub, Releases, Draft a new release, choose the existing tag, paste the 0.1.0 section of `CHANGELOG.md`).
