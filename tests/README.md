# Tests

Test levels (ADR-046). All use the mock LLM provider unless a test says otherwise; nothing here calls a live model.

| Level | Where | Marker | Runs |
|---|---|---|---|
| Unit and cross-module (fakes) | `tests/unit/`, mirrors `src/aitaf` | `blackbox` or `whitebox` | default `pytest` and every CI push |
| Integration (real Chromium, one component or the pipeline) | `tests/integration/` | `integration` | `pytest -m integration`, `integration.yml` |
| System (the whole pipeline end to end, scenarios S1 to S9) | `tests/system/` | `system` | `pytest -m system`, `integration.yml` |
| Acceptance (one check per functional requirement, run by the author as customer; ADR-047) | `tests/acceptance/` (35 fast tests) and `tests/system/test_acceptance_browser.py` (4 tests that need Chromium, also marked `system`) | `acceptance` | `pytest -m acceptance` (the browser ones with `-m system`) |

`tests/support/` holds shared fixtures (a fake-browser project, seeded pipeline records, `pipeline_runner.py` that runs the real command line and the whole pipeline for the system and acceptance tests). The first docstring line of an acceptance test is `AT-FR-nn: <criterion>`; a `PARTLY:` line names what it does not demonstrate. `python -m aitaf.quality.acceptance_matrix --junit <files> --out docs/project-management/ACCEPTANCE_MATRIX.md` builds the matrix. Every test carries `blackbox` (public behaviour from an acceptance criterion) or `whitebox` (an internal branch or validator). The default run excludes `integration` and `system` because they need Chromium and take minutes.

System scenarios: S1 happy path (20 requirements to report and Dashboard), S2 healing on a changed page, S3 human gate, S4 provider outage (honest label), S5 hostile and invalid input, S6 host outside the allow-list, S7 killed run, S8 repeatability, S9 approving a repair. S10 is the container smoke test, the `docker` job in `integration.yml`.
