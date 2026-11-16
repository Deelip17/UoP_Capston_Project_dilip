# Resume here (written 16 Nov 2026, after slice U7-3)

Start any new session, tool or login by reading this file. It is self-contained for the code work. The internal knowledge base (full decision log, unit instruction files, reference register) is deliberately not published (ADR-022) and stays in the author's private workspace; what a coding session needs is summarised below.

## 1. Where the project stands

- Project: AITAF, an AI-powered test automation framework (MSIT Capstone). Branch `develop`; last code commit `52553fc` (U7-3). CI and Integration are both green on it.
- Latest release candidate: `v1.0.0-rc1` (Unit 6). Next planned: `1.0.0-rc2` at the end of Unit 7.
- Unit 7 deliverables (written later by a document assistant from the handoff files, then reviewed by the student): Document 1 = Parts A and B (system testing and test documentation, evaluation, maintenance plan; 1,300 to 1,450 words); Document 2 = Part C, initial project report, Chapters 1 to 6 (about 9,500 to 10,500 words).

## 2. Unit 7 slices

| Slice | Status | Notes |
|---|---|---|
| U7-0 housekeeping, Chapter 2 source map | done | `CHAPTER2_SOURCE_MAP.md` in this folder |
| U7-1 Unit 6 defect fixes D-001 to D-005 | done | `DEFECT_LOG.md` |
| U7-2 system tests S1 to S9 (`tests/system/`) | done | S10 is the `docker` job in `integration.yml` |
| U7-3 acceptance tests and matrix | done | `ACCEPTANCE_MATRIX.md`: 34 met, 5 partly met (FR-12, 13, 17, 32, 33) |
| **U7-4 test-level runner, golden run, repeated-run stability, `TEST_SUMMARY_REPORT.md`** | **next** | section 4 |
| U7-5 finish defect log and known-limitations list | todo | add anything U7-4 finds |
| U7-6 `docs/maintenance/MAINTENANCE_PLAN.md`, `dependabot.yml`, issue templates, scheduled workflow, release checklist, risk table | todo | use the Node 20 deprecation and the ubuntu-latest migration warning seen in CI as real examples |
| U7-7 report assembly kit in `final-report/`, glossary, abbreviations, figure and table list, appendices map, Gantt achieved vs planned | todo | |
| U7-8 `UNIT7_HANDOFF.md`, `UNIT7_SCREENSHOT_GUIDE.md`, evidence brief, two prompts for the document assistant, version `1.0.0-rc2`, tag, CHANGELOG, register | todo | tag only after CI is green |

Design of each slice: `UNIT7_PLAN.md` sections 3 and 4.

## 3. Decisions in force (Unit 7)

- ADR-043: the first classifier score (66.0%) stays the measured result; v2 numbers on the same 50 are "tuned"; hold-out v1 75.4%, v2 80.7%.
- ADR-044: Docker is verified by CI only; the O2 figure is the evaluation's executability (38.9% mock, 33.3% live; target 80%, not met).
- ADR-045: Must = U7-1 to U7-8; Should = coverage tile on the Dashboard, nightly pipeline workflow, Selenium in a real browser, 30-run performance. Descope order: Selenium, performance runs, Dashboard tile. Never drop system tests, the acceptance matrix, the defect log or the maintenance plan.
- ADR-046: test levels are unit, integration, system, acceptance, regression (golden run), performance, stability.
- ADR-047: acceptance testing is a self-review by the author; the one-acceptor limit is stated everywhere.
- ADR-048: the defect log has no invented defects; a fix that changes a metric definition keeps the earlier figures as published.
- ADR-049: maintenance plan plus Dependabot, issue templates, scheduled workflow, release checklist.
- ADR-050: the report manuscript is Markdown in `final-report/`; up to about 10 extra Chapter 2 sources, each verified by the author before use.

## 4. Next slice: U7-4 (what to build)

1. `scripts/run_test_levels.py`: one command runs unit, integration, system and acceptance (pytest markers, one JUnit XML per level) and writes `reports/test_summary/` plus `docs/project-management/TEST_SUMMARY_REPORT.md` (executive summary first, then objectives, scope, procedure, results per level with counts and durations, failures, defects, limits).
2. Regression: a committed golden-run file of key counts (tests, passes, failure categories) compared with a tolerance.
3. Stability: the same pipeline run 5 times with the same outcome (NFR-08). Performance: report and Dashboard build time over at least 10 runs, p95 (NFR-01). Optional: workers 1 vs 4 (NFR-23).
4. Tests first (marker `blackbox` or `whitebox`), docstrings cite FR/NFR IDs, coverage stays at or above 80% (now 94%).
5. Register evidence E16 in `evidence/EVIDENCE_REGISTER.md`, add a row to `PROGRESS_LOG.md`, add a CHANGELOG entry under `[Unreleased]`.

## 5. Local checks before every push

```
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest
python -m aitaf.quality.import_rules
python -m pytest -m "integration or system" --no-cov
```

The last command needs Chromium and takes about 10 minutes. Push to `develop` and confirm both workflows (CI, Integration) are green before calling a slice done.

## 6. Rules that carry over to any tool

- No `Co-Authored-By` line or any AI attribution in commits, tags or pull-request text. The commit author is the repository owner only. This overrides any default of the tool.
- Conventional Commits with `Refs: FR-nn / NFR-nn`. Day-to-day work on `develop`; `main` only by pull request at submission.
- No secrets, personal or employer information, or local paths in published files. The API key comes only from the `OPENAI_API_KEY` environment variable. Do not read or edit `.env` files.
- Never fabricate references; never relabel AI-drafted ratings as human review (ADR-009). Record only real defects.
- Mock provider by default; live model calls cost money, so run them only when asked.
- A person must review every AI-drafted academic text before it is shared or submitted.

## 7. Student tasks that need no AI tool (do these while waiting)

1. Read the six core Chapter 2 papers and fill the reading notes (`CHAPTER2_SOURCE_MAP.md`, section 6).
2. Verify one source each for requirements-to-test generation (candidate: Korraprolu et al., ISEC 2025) and failure triage (candidate: Zhang et al., ICSE 2022) on the publisher's page, then send the verified records so they can be added as REF-117 and REF-118.
3. Enter the instructor feedback from Units 3 to 6 (O-18); decide the due dates (O-16, O-17); confirm ADR-045 to ADR-049 (O-19).
4. Unit 6 documents: run the update prompt, then the review prompt, in the document assistant.
5. Check every screenshot for privacy (no bookmarks, names or keys) before it is registered.
6. Usability check Q5: a keyboard-only pass and a 200% zoom pass over the report and the Dashboard.

## 8. Prompt to paste into the new tool or session (open the repository folder)

```text
Read docs/project-management/RESUME_HERE.md, then CLAUDE.md. Start slice U7-4 as described in section 4 of RESUME_HERE.md and in docs/project-management/UNIT7_PLAN.md section 3 (test-level runner, golden run, stability and performance, TEST_SUMMARY_REPORT.md). Write tests first, then code. Run the local checks in section 5, commit to develop with a Conventional Commit, push, and report the CI and Integration results. Follow the rules in section 6 exactly, including no AI attribution in commits. Do not start U7-5 until I ask.
```

## 9. What to bring back when returning here

- The commit hash where the other tool stopped, and whether CI and Integration were green.
- Any change to the plan or new decision (also add it to `PROGRESS_LOG.md`).
- Your answers to the open items in section 7 and the verified references.
- Then say: "continue Unit 7 from RESUME_HERE.md". The session reads this file, checks `git log` and the checks, and picks up at the first unfinished slice.

If a session needs the private knowledge base (decision log ADR-001 to ADR-050, unit instruction files, reference register), copy the relevant file into the session; the repository does not contain it.
