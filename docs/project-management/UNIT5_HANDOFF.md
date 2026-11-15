# Unit 5 handoff for writing the paper

**Purpose:** everything needed to write the Unit 5 paper (core algorithm implementation, unit testing, version control) without inventing anything. Quote only what is in this file, in `PROGRESS_LOG.md`, or in the evidence files. Anything under "Do not claim" must not appear as an achievement.
**State described:** release `v0.5.0` (commit `581f082`), plus documentation commits after it. **Repository (public):** https://github.com/Deelip17/UoP_Capston_Project_dilip

## 1. Summary

Four of the eight modules exist as working code (Requirement Analyzer, Test Case Generator, Script Generator, a Self-Healing core) together with the cross-cutting parts they need: masking and validation layer, LLM Gateway, SQLite persistence, metrics, a command-line interface. Everything runs on a deterministic **mock** LLM provider: no real model output has been produced. Tests were written first in every slice; the suite has 616 tests, all green on GitHub Actions (Ubuntu and Windows), at 97.86% coverage.

## 2. Modules built and requirement coverage

"Done" means implemented and tested on the mock provider or on fixtures. Totals over the 39 functional requirements: **21 done, 6 partly, 12 not built**.

| Module / package | Requirements | Status |
|---|---|---|
| Requirement Analyzer (`analyzer`) | FR-01, 02, 03, 04, 05 | Done |
| Test Case Generator (`generator`) | FR-06, 07, 08, 09, 10, 11 | Done |
| Script Generator (`scriptgen`) | FR-14, 15, 16 done; FR-12, 13 partly (scripts generated and validated, never run in a browser) | Done / partly |
| Self-Healing core (`healing`) | FR-22, 23, 24, 25 done (approval through the Python API only); FR-26 partly (limits and a success-rate function, not in a report) | Done / partly |
| Cross-cutting (`core`) | FR-30, 36, 37 done; FR-19 partly (storage exists, nothing writes results); FR-34 partly (IDs link requirement, case, script; not execution, failure, report); FR-35 partly (`analyze`, `generate`, `review`, `script`, `metrics`, `heal` work; `run`, `execute`, `diagnose`, `report` print "not implemented") | Done / partly |
| Not built | FR-17, 18, 20, 21 (Execution Engine), FR-27, 28, 29 (Failure Analyzer), FR-31, 32, 33 (Reporting Engine, Dashboard), FR-38, 39 (mutation harness, Unit 6 metrics) | Not built |

Non-functional requirements shown: NFR-07 (kill-process durability test), 09, 10, 11 (static checks and confined writes; no execution-time sandbox yet), 12, 13 (fixture-based only), 14, 15, 17 (automated import-rule check in CI, zero violations), 18, 19, 24, 30, 31. Partly: NFR-25 (mock provider and a test double share the interface; no OpenAI provider), NFR-32 (coverage gaps reported per run, not assessed), NFR-34, NFR-35 (four components and the gateway emit metrics). Not built: NFR-06 (retry with back-off), NFR-03 (not measured on a mutation catalogue).

## 3. Tests and coverage (Part B facts)

- **616 tests: 391 black-box, 225 white-box.** 64 of them are parametrised documentation checks (one docstring check per module, README checks), so there are **552 behaviour tests**. Per area (collected counts): core 143, masking 46, analyzer 29, generator 38, scriptgen 59, healing 163, quality tools 94 (30 behaviour plus the 64 documentation checks), command line, smoke and metrics pipeline 44.
- **Coverage 97.86%** (line and branch, gate 80%); healing modules 93 to 100% (NFR-18 asks 90%). Evidence E08.
- **Definitions used:** *black-box* tests drive the public behaviour from the requirement's acceptance criteria (for example, "an injected locator change is classified as a locator failure; an injected assertion failure is not"); *white-box* tests exercise internal branches and validators (for example, the similarity components, the masking patterns, migration versions). Every test carries a `blackbox` or `whitebox` marker; `--strict-markers` makes an unknown marker an error.
- **Techniques worth describing:** tests first from acceptance criteria; the repository contract tests run against both an in-memory fake and a real SQLite file; a subprocess is killed mid-run to check database integrity (NFR-07); forbidden-construct fixtures for generated code; seeded duplicates, seeded secrets and prompt-injection fixtures; fault injection of provider failures; generated test functions run against fake Playwright and Selenium drivers; a pipeline test that every component emits metrics.
- **How tests improved reliability (real examples, see section 5):** an end-to-end test exposed a missing run ID in the command line; a CI run exposed a test that depended on the environment.

## 4. Evidence (author captures the screenshots)

Text logs and generated files are in the repository; the paper needs **screenshots inside the document**, so each ID below still needs a terminal or browser capture unless noted. Register: `evidence/EVIDENCE_REGISTER.md`.

| ID | Shows | Repository file | Capture |
|---|---|---|---|
| E04 | Analyzer input to output; injected requirement rejected | `evidence/unit05/logs/E04_analyzer_run_20261114.txt` | Run `python -m aitaf analyze --input data/requirements/sample_requirements.md --db demo.db` |
| E05 | Test cases linked to requirement IDs; exports | `.../E05_test_case_generation_20261114.txt`, `evidence/unit05/E05_exports/` | `generate`, then `review --list` |
| E06 | Generated scripts, page object, locator repository; rejection reasons | `.../E06_script_generation_20261114.txt`, `evidence/unit05/E06_generated/` | `script`, plus the generated files in VS Code |
| E07 | Pytest results, black-box and white-box counts | `.../E07_pytest_final_20261114.txt` (and per-slice logs) | `pytest -v` |
| E08 | Coverage report with percentage | `.../E08_coverage_20261114.txt` | Open `reports/htmlcov/index.html` after `pytest --cov=aitaf --cov-report=html:reports/htmlcov` |
| E09 | Self-healing scenarios and the approval gate | `.../E09_self_healing_20261114.txt` | `heal` commands in the log |
| E17a | Tag `v0.1.0` | `.../E17a_tag_v0.1.0_20261114.txt` | GitHub tags page |
| E17b | Release `v0.5.0` with wheel, evidence bundle and notes | `.../E17b_release_v0.5.0_20261114.txt` | The release page (link below) |
| E13a | Early metrics sample (illustrative prices) | `.../E13a_metrics_sample_20261114.txt` | optional; real dataset is Unit 6 |

Label every output **mock** in captions. Capture code (VS Code, larger font) beside the output, with a caption naming the requirement IDs.

## 5. Real issues and challenges (the only ones that may be quoted)

**Issues found by tests (Part B)** (full text in `PROGRESS_LOG.md`):

1. Ruff B017 failed the lint gate: tests used `pytest.raises(Exception)`; tightened to the pydantic error type.
2. CI run 7 was red on Ubuntu and Windows while a CLI test passed locally: CI sets `LLM_PROVIDER=mock`, which overrides the config file, so the test was not isolated; fixed with an environment-clearing fixture.
3. `aitaf analyze` failed with "no run ID is set": the command generated a run ID but never bound it; only the end-to-end CLI test caught it.
4. An empty-selector test case raised a pydantic error: the test expectation was wrong, not the code (say so honestly if quoted).
5. Unit 4 demonstration (not a surprise): the deliberately failing test for evidence E03b; label it as deliberate.

**Challenges (Part A)**: choose the three or four that best show the core logic, from the table in `PROGRESS_LOG.md`: generated code is untrusted (structured plan, templates, AST allow-list); healing must not hide defects (classification first); similarity alone accepted a wrong element at 0.67 (separate validation layer); a stored fallback can match two elements (proposed locator must be unique); the mock provider needed deterministic per-component responders so the pipeline completes offline. Do not add challenges that are not in the log.

## 6. Version control (Part C facts)

- **Branching:** `main` and `develop`; day-to-day work on `develop` (ADR-028), merged to `main` by pull request at submission; earlier work used `feature/ci-workflow` and a `chore/ci-red-demo` branch for the CI failure evidence. Conventional Commits with a `Refs:` line citing FR and NFR IDs; about one commit per slice (two slices needed a follow-up fix commit); no AI co-author lines (ADR-021).
- **Tags (annotated, on `develop` by ADR-033):** `v0.1.0` at `f31a76d` (slices 1 to 3: 156 tests, CI run 9 green, **tag only, no release page**); `v0.5.0` at `581f082` (slices 1 to 7: 552 tests then, CI run 14 green). The older tag `Intial_folder_structure` is from Unit 3 (the spelling is as created).
- **Release:** https://github.com/Deelip17/UoP_Capston_Project_dilip/releases/tag/v0.5.0, published by `release.yml` (run https://github.com/Deelip17/UoP_Capston_Project_dilip/actions/runs/43670876225): re-runs lint, types, import rules, tests with the 80% gate and the dependency audit; refuses a tag that does not match `aitaf.__version__` or has no changelog section; attaches the wheel and an evidence bundle; notes come from `CHANGELOG.md`.
- **CI:** https://github.com/Deelip17/UoP_Capston_Project_dilip/actions/runs/43670668717 (run 14, Ubuntu and Windows matrix).
- **How tags and releases help monitoring:** the tag-to-version check and the changelog section make each release traceable to a commit, a test count and a coverage figure; a failed verify job blocks the release (links to REF-019).

## 7. Suggested structure and word budget

Total near **1,450 words** (limit 1,400 to 1,500, excluding references and title), double-spaced Times New Roman 12 pt, all screenshots inside the document. Part A about **550** (core logic, alignment with the objectives, code and output figures, challenges), Part B about **500** (test types, issues found and what they changed, how unit tests improve reliability), Part C about **350** (branching, tags, release, monitoring). Rubric rows: Q1 core logic, Q2 unit testing, Q3 version control, Sources and Evidence, Connection to course materials.

## 8. Reading map (course references first, ADR-020)

| Reference | Use it for |
|---|---|
| REF-006 Summers (2020), Chapter 10, Verification and Validation | Part B: validation versus verification, test types |
| REF-017 Rana (2023), test cases | Parts A and B: test case structure (ID, prerequisites, steps, input, expected result), which the `TestCase` record follows |
| REF-018 Amazon Web Services (n.d.), unit testing | Part B: isolation, mocks and stubs (mock provider, fake repository) |
| REF-019 Swiftful Thinking (2024), tags, versioning and releases | Part C |

No new external references unless the rubric requires one.

## 9. Do not claim

- That a real language model produced any output. Everything used the mock provider; no OpenAI provider exists and no live call was made (the optional live smoke test E04b was not done).
- That scripts were executed in a real browser or against a sample application, or that FR-12 and FR-13 acceptance is fully met.
- That the Execution Engine, Failure Analyzer, Reporting Engine, Dashboard, `aitaf run` or the mutation harness exist.
- A healing success rate, repair-time measurement (NFR-03) or classification accuracy: healing ran on six hand-made fixtures; its thresholds are untuned initial values.
- That the metrics cover all components (four plus the gateway), or that prices in E13a are real.
- That masking finds names or addresses, or that prompt-injection resistance is guaranteed (fixtures only).
- That retry with back-off (NFR-06) or a CLI or report page for approving healing events exists.
- That `v0.1.0` has a release page, or that `main` contains this work (it is on `develop`).
- Any legal or privacy conclusion (GDPR wording needs the Data Privacy Officer).

## 10. Author to-do before submission

Capture the screenshots in section 4; review the AI-generated parts of the paper (ADR-009); fill the title page; optionally create a release page for `v0.1.0` by hand; create `unit5-submitted` after submission if that tag convention is kept.
