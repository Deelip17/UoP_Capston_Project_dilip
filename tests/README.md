# Tests

Test levels (ADR-046). All use the mock LLM provider unless a test says otherwise; nothing here calls a live model.

| Level | Where | Marker | Runs |
|---|---|---|---|
| Unit and cross-module (fakes) | `tests/unit/`, mirrors `src/aitaf` | `blackbox` or `whitebox` | default `pytest` and every CI push |
| Integration (real Chromium, one component or the pipeline) | `tests/integration/` | `integration` | `pytest -m integration`, `integration.yml` |
| System (the whole pipeline end to end, scenarios S1 to S9) | `tests/system/` | `system` | `pytest -m system`, `integration.yml` |
| Acceptance (one check per requirement group, run by the author) | `tests/acceptance/` (Unit 7, slice U7-3) | `acceptance` | `pytest -m acceptance` |

`tests/support/` holds shared fixtures (a fake-browser project, seeded pipeline records). Every test carries `blackbox` (public behaviour from an acceptance criterion) or `whitebox` (an internal branch or validator). The default run excludes `integration` and `system` because they need Chromium and take minutes.

System scenarios: S1 happy path (20 requirements to report and Dashboard), S2 healing on a changed page, S3 human gate, S4 provider outage (honest label), S5 hostile and invalid input, S6 host outside the allow-list, S7 killed run, S8 repeatability, S9 approving a repair. S10 is the container smoke test, the `docker` job in `integration.yml`.
