# Evidence session brief (screenshots only)

Paste this file's path or content into a new Claude Code session opened in the repository folder. That session does **screenshots only**. It must not change code, tests, docs or version numbers.

## 1. Goal

Capture the Unit 5 evidence screenshots from the public GitHub repository (and one local coverage page) and save them in `evidence/unit05/screenshots/`.

- Repository: https://github.com/Deelip17/UoP_Capston_Project_dilip (public)
- Full shot list, captions and optional shots: `docs/project-management/UNIT5_SCREENSHOT_GUIDE.md` (section 2)
- Register afterwards in `evidence/EVIDENCE_REGISTER.md` only if the user asks.

## 2. Hard rules

1. Never add `Co-Authored-By` or any AI attribution to commits, tags or PR text. Do not commit or push unless the user asks.
2. Do not log in to GitHub. Capture only what an anonymous visitor sees (this also proves the repo is public). Use a fresh browser context, so no cookies or avatar.
3. Do not expose the Windows user name or any local path in a capture. For the local coverage page, capture only the page content, not the address bar.
4. No secrets. If a page unexpectedly shows one, stop and tell the user.
5. Do not edit anything on GitHub (no clicks on star, fork, issue, PR buttons).

## 3. Setup

```
pip install playwright
playwright install chromium
```

Use Chromium through Playwright (or `channel="chrome"` if installed). Use a **fresh, non-persistent context**:

- viewport 1440 x 900, `device_scale_factor` 1.25 (reads like 120% zoom), light colour scheme (`color_scheme="light"`)
- wait for `networkidle` and then 1 second before each capture
- save PNG files with the exact names in section 5

## 4. Known limitations to handle

| Issue | What to do |
|---|---|
| Playwright screenshots do not include the browser address bar | Inject a thin banner at the top of the page showing the real page URL (small DOM element), then capture. State in the final report that the banner was added. |
| GitHub Actions **job logs** need a signed-in user, even on public repos | The run summary page (`/actions/runs/<id>`) is visible anonymously. For `E07_ci_pytest_log.png`, try it; if the log pane is blocked, skip and report it. The user captures it manually, or use the text log `evidence/unit05/logs/E07_pytest_final_20261114.txt` instead. |
| Line ranges (`#L137-L164`) highlight lines but may sit below the fold | Scroll the highlighted block into view (`scrollIntoView`) before capture. |
| Code view may collapse long files | Use the `/blob/...` page, not `/raw/`. |
| Local coverage page is a file, not on GitHub | Open `reports/htmlcov/index.html` with a `file://` URL. If missing, tell the user to run `pytest --cov=aitaf --cov-report=html:reports/htmlcov` (do not run it yourself unless asked). |

## 5. Required shots (14)

Base = `https://github.com/Deelip17/UoP_Capston_Project_dilip`

| File | URL (after Base) |
|---|---|
| `E04_analyzer_code.png` | `/blob/v0.5.0/src/aitaf/analyzer/analyzer.py#L137-L164` |
| `E04_analyzer_output.png` | `/blob/develop/evidence/unit05/logs/E04_analyzer_run_20261114.txt` |
| `E06_validator_code.png` | `/blob/v0.5.0/src/aitaf/scriptgen/validator.py#L113-L149` |
| `E06_script_output.png` | `/blob/develop/evidence/unit05/logs/E06_script_generation_20261114.txt` |
| `E09_similarity_code.png` | `/blob/v0.5.0/src/aitaf/healing/similarity.py#L69-L85` |
| `E09_healing_output.png` | `/blob/develop/evidence/unit05/logs/E09_self_healing_20261114.txt` |
| `E07_ci_summary.png` | `/actions/runs/43672019877` (all jobs green, 616 tests) |
| `E07_ci_pytest_log.png` | same run, job "test (ubuntu-latest)", step "Unit tests with coverage" (see limitation) |
| `E07_blackbox_whitebox_code.png` | `/blob/v0.5.0/tests/unit/healing/test_engine.py#L218-L244`, then `#L434-L453` (two captures, or one stitched) |
| `E08_coverage_html.png` | local `reports/htmlcov/index.html` (total 97.86%, no address bar) |
| `E17_repo_home.png` | `/` (shows "Public") |
| `E17_branches.png` | `/branches` |
| `E17a_tags.png` | `/tags` |
| `E17b_release_v0.5.0.png` | `/releases/tag/v0.5.0` (notes and both assets visible) |

Optional shots (7) are in the guide. Take them only if asked.

## 6. Values to confirm before starting (the coding session fills these in)

The coding session may add commits, a new tag or newer CI runs. Before capturing, check the page is still correct:

- Latest tag shown on `/tags`: `________` (expected v0.5.0 unless the coding session added more)
- CI run to use for `E07_ci_summary.png`: `________` (default 43672019877, run #16)
- Latest green CI run on `develop` (optional shot): `________`
- Changed line ranges (only if code in the three files moved): `________`

If a tagged URL (`/blob/v0.5.0/...`) no longer shows the expected lines, stop and ask rather than guessing.

## 7. Check each capture

For every PNG: open it, confirm the target content is visible and readable, no avatar or sign-in prompt, no local path. Retake if not.

## 8. Final report (to the user)

List each file saved, any shot skipped and why, that banners were injected for the address bar, and the next step: ask the coding session to "register the screenshots" and commit, then give Cowork the prompt from section 5 of `UNIT5_SCREENSHOT_GUIDE.md`.
