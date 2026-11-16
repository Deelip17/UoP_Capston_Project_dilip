# Unit 6 evidence session brief (screenshots only)

Paste this file's path or content into a new Claude Code session opened in the repository folder. That session does **screenshots only**. It must not change code, tests, docs or version numbers, and must not commit or push unless the user asks.

## 1. Goal

Capture the Unit 6 screenshots listed in `docs/project-management/UNIT6_SCREENSHOT_GUIDE.md` (section 2) that do not need a sign-in, and save them in `evidence/unit06/screenshots/` with the exact file names given there. Repository: https://github.com/Deelip17/UoP_Capston_Project_dilip (public). Release candidate: tag `v1.0.0-rc1` (commit `86a6095`).

## 2. Hard rules

1. Never add `Co-Authored-By` or any AI attribution to commits, tags or PR text. Do not commit or push.
2. Do not log in to GitHub. Use a fresh, non-persistent browser context: no cookies, no avatar. Pages that need a sign-in (Actions job logs) are **skipped and reported**; the user captures them.
3. No user name, no local path and no bookmarks in any image. For local pages capture only the page content (the address bar is not captured; the banner below stands in for it).
4. No secrets. If a page unexpectedly shows one, stop and tell the user.
5. Do not click anything that changes GitHub (star, fork, issue, pull request).
6. Do not run `aitaf run`, Docker, tests or the evaluation: use the evidence already in the repository.

## 3. Setup

```
pip install playwright
playwright install chromium
```

Chromium through Playwright, fresh context, viewport 1440 x 900, `device_scale_factor` 1.25, `color_scheme="light"`. Wait for `networkidle` and 1 second before each capture. Save PNG files with the names in the table below.

## 4. Known limitations to handle

| Issue | What to do |
|---|---|
| Playwright screenshots omit the address bar | Inject a thin banner at the top of the page showing the real URL (or the repository-relative path for local files); say so in the final report |
| GitHub Actions **job logs** need a sign-in | Capture only the run summary pages; skip figure 33 and report it |
| Line ranges (`#L267-L293`) may sit below the fold | `scrollIntoView` the highlighted block before capturing; keep about 45 lines per image |
| Text files on GitHub (`.txt`, `.csv`, `.md`) | Use the `/blob/...` page, not `/raw/` |
| Local HTML files | Open `file:///<repository folder>/evidence/unit06/...` (build the path from the repository root); capture the page body only |
| `.env.example` | Skip figure 31 unless `/blob/develop/.env.example` exists (the user has to commit it first) |

## 5. Required shots

Base = `https://github.com/Deelip17/UoP_Capston_Project_dilip`. **Tag blobs** use `/blob/v1.0.0-rc1/...`; **evidence** uses `/blob/develop/...`.

| File | Address or file |
|---|---|
| `E10b_run_console.png` | `/blob/develop/evidence/unit06/E10_pipeline/run3_console.txt` (top) |
| `E10b_run_stages.png` | same file, scrolled to the `== execute`, `== diagnose` and `== report` headings |
| `E11_report_top.png` | local `evidence/unit06/E10_pipeline/run3_report/report.html` (top) |
| `E11_report_failure.png` | same page, one failure section with analysis and screenshot |
| `E11b_dashboard_top.png` | local `evidence/unit06/E11_dashboard/dashboard.html` (top) |
| `E11b_dashboard_trend.png` | same page, charts and run table |
| `E12_engine_loop.png` | `/blob/v1.0.0-rc1/src/aitaf/execution/runner.py#L267-L293` |
| `E12_engine_heal.png` | `/blob/v1.0.0-rc1/src/aitaf/execution/runner.py#L337-L383` |
| `E12_failure_rules.png` | `/blob/v1.0.0-rc1/src/aitaf/diagnosis/rules.py#L143-L195` |
| `E12_report_metrics.png` | `/blob/v1.0.0-rc1/src/aitaf/reporting/metrics.py#L75-L110` |
| `E12_dashboard_collect.png` | `/blob/v1.0.0-rc1/src/aitaf/dashboard/data.py#L49-L81` |
| `E12_eval_harness.png` | `/blob/v1.0.0-rc1/src/aitaf/evaluation/classify_eval.py#L88-L139` |
| `E12_gateway_call.png` | `/blob/v1.0.0-rc1/src/aitaf/core/llm/gateway.py#L56-L79` |
| `E12_repo_write_read.png` | `/blob/v1.0.0-rc1/src/aitaf/core/storage/sqlite.py#L240-L268` |
| `E12_healer_interface.png` | `/blob/v1.0.0-rc1/src/aitaf/core/healing.py#L46-L75` |
| `E12_pipeline.png` | `/blob/v1.0.0-rc1/src/aitaf/pipeline.py#L71-L110` |
| `E12_approve_heal.png` | `/blob/v1.0.0-rc1/src/aitaf/healing/approval.py#L25-L69` |
| `E12_scriptgen_catalogue.png` | `/blob/v1.0.0-rc1/src/aitaf/scriptgen/catalogue.py#L139-L155` |
| `E13_results_healing.png` | `/blob/develop/evaluation/results/RESULTS.md` (healing section) |
| `E13_results_classification.png` | same file (classification sections) |
| `E13_results_generation.png` | same file (generation sections) |
| `E13_chart_healing.png` | `/blob/develop/evaluation/results/charts/healing_by_kind.png` |
| `E13_chart_classification.png` | `/blob/develop/evaluation/results/charts/classification.png` |
| `E13_chart_generation.png` | `/blob/develop/evaluation/results/charts/generation.png` |
| `E15_dockerfile.png` | `/blob/v1.0.0-rc1/Dockerfile` |
| `E15_deployment_guide.png` | `/blob/v1.0.0-rc1/docs/user-guide/DEPLOYMENT.md` (sections 1 and 3) |
| `E15_ci_integration.png` | `/actions/runs/43800603134` (summary page, both jobs green) |
| `E17c_release_rc1.png` | `/releases/tag/v1.0.0-rc1` (notes and both assets visible) |
| `E17c_tags.png` | `/tags` |
| `E07_ci_summary.png` | `/actions/runs/43800603157` (CI #47, all jobs green) |
| `E17_repo_home.png` | `/` ("Public" visible) |

**Not for this session** (the user captures these): `E15_ci_docker_job.png` (sign-in), `E15_install_terminal.png`, `E07_coverage.png` (terminal), `E14_qualitative_sheet.png` (after the human review), `E10_login_page.png` (optional).

## 6. Final report to the user

List: files saved (with sizes), files skipped and why, whether each tagged URL showed the expected lines (if a `/blob/v1.0.0-rc1/...#L...` page does not show the expected code, stop and ask rather than guess), the banner text used, and any page that showed something unexpected (a user name, a path, a secret).
