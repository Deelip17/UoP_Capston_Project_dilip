# execution

The Execution Engine: it runs generated test scripts with PyTest, keeps the browser inside an allow-list, and stores every result with its evidence (FR-17 to FR-21, NFR-11).

| Module | Purpose | Requirements |
|---|---|---|
| `config` | `RunConfig`: scripts directory, base URL, allowed hosts, driver, headless, timeout, retries, workers, checkpoints, run time limit; every value bounded | FR-17, FR-20 |
| `allowlist` | `check_base_url`: refuses a run before anything starts if the host is not on the allow-list (parsed host, http and https only, no credentials, no look-alike hosts) | FR-21, NFR-11 |
| `plugin` | PyTest plugin (`-p aitaf.execution.plugin`): one result line per test, screenshot and DOM snapshot of a failing test (Playwright `page` or Selenium `driver`), evidence names confined to the evidence directory | FR-18, FR-19 |
| `runner` | `ExecutionEngine.execute`: allow-list check, PyTest subprocess (optional xdist workers, hard time limit, secrets removed from the environment), retries of failing tests, masked failure text, results stored with attempts and evidence links | FR-17 to FR-21, NFR-04, NFR-11, NFR-23 |

## Use

```text
aitaf script  --out-dir generated_tests --base-url http://127.0.0.1:8765
aitaf execute --scripts generated_tests --base-url http://127.0.0.1:8765 [--retries 2] [--workers 4] [--headed] [--checkpoints]
```

`aitaf execute` creates a new run, writes screenshots, DOM snapshots and JUnit XML to `reports/runs/<run id>/`, stores the results in SQLite and exits 0 only if every test passed. The generated `conftest.py` also blocks Playwright requests to hosts outside the allow-list.

## Tests

`tests/unit/execution/`: allow-list and configuration; the plugin in-process with `pytester`; the engine with a fake browser fixture over real PyTest subprocesses (outcomes, evidence, retries, workers, time limit, secret removal and masking); the command line. `tests/integration/` (marker `integration`, needs Chromium, excluded from the default run): a real browser against the local sample shop, including a failing test with a real screenshot and a blocked navigation to an unlisted host.

## Not built

- The Self-Healing Engine is not called during a run yet: a locator failure fails the test. Integration is the next slice.
- Selenium runs are supported by the generated `conftest.py` and the plugin, but were exercised only with a fake driver; the Selenium conftest cannot intercept requests, so only the base-URL check protects it.
- Parallel workers are tested with a fake browser; speed-up (NFR-23) has not been measured.
- Video and Playwright trace capture (FR-18, optional) are not implemented.
- Results record the final attempt of each test; per-attempt history is kept only in the raw result lines and JUnit files.
- Only the checks named above guard the browser; there is no network-level sandbox.
