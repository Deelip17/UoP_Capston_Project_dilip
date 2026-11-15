# execution

The Execution Engine: it runs generated test scripts with PyTest, keeps the browser inside an allow-list, and stores every result with its evidence (FR-17 to FR-21, NFR-11).

| Module | Purpose | Requirements |
|---|---|---|
| `config` | `RunConfig`: scripts directory, base URL, allowed hosts, driver, headless, timeout, retries, workers, checkpoints, run time limit, healing on or off and its pass limit; every value bounded | FR-17, FR-20 |
| `allowlist` | `check_base_url`: refuses a run before anything starts if the host is not on the allow-list (parsed host, http and https only, no credentials, no look-alike hosts) | FR-21, NFR-11 |
| `plugin` | PyTest plugin (`-p aitaf.execution.plugin`): one result line per test, screenshot and DOM snapshot of a failing test (Playwright `page` or Selenium `driver`), evidence names confined to the evidence directory | FR-18, FR-19 |
| `runner` | `ExecutionEngine.execute`: allow-list check, PyTest subprocess (optional xdist workers, hard time limit, secrets removed from the environment), retries of failing tests, locator failures offered to a healer and rerun on a temporary copy of the scripts, masked failure text, results stored with attempts and evidence links | FR-17 to FR-21, FR-22 to FR-26, NFR-04, NFR-11, NFR-23 |

## Use

```text
aitaf script  --out-dir generated_tests --base-url http://127.0.0.1:8765
aitaf execute --scripts generated_tests --base-url http://127.0.0.1:8765 [--retries 2] [--workers 4] [--headed] [--checkpoints]
aitaf execute ... --heal --baseline data/dom/shop [--max-heal-passes 5]
```

**Healing during a run.** A generated page object that finds no element raises `LookupError("no locator strategy matched for <name> on page <page>")`. With `--heal` the engine reads that locator from the scripts' `locators/<page>_locators.py` (parsed, never executed), passes it with the failing page's DOM snapshot and, if `--baseline` is given, the original element's signature to the healer. If a replacement is proposed, the engine writes it as the primary locator in a **temporary copy** (`healed_scripts/` in the evidence directory), keeps the old primary as a fallback, and reruns the failing tests there. The original scripts and the locator repository are never changed; every event is stored as proposed and unapproved (FR-25). Assertion failures are never sent to the healer. One question is asked per locator per pass, and `--max-heal-passes` bounds the reruns.

`aitaf execute` creates a new run, writes screenshots, DOM snapshots and JUnit XML to `reports/runs/<run id>/`, stores the results in SQLite and exits 0 only if every test passed. The generated `conftest.py` also blocks Playwright requests to hosts outside the allow-list.

## Tests

`tests/unit/execution/`: allow-list and configuration; the plugin in-process with `pytester`; the engine with a fake browser fixture over real PyTest subprocesses (outcomes, evidence, retries, workers, time limit, secret removal and masking); the command line. `tests/integration/` (marker `integration`, needs Chromium, excluded from the default run): a real browser against the local sample shop, including a failing test with a real screenshot and a blocked navigation to an unlisted host.

## Not built

- Approving a healing event from an execution run is not possible yet: the event belongs to the execution run, while the stored locators belong to the script-generation run, so `approve_healing_event` cannot find them. The healed copy is evidence of what would pass, not a permanent repair.
- Healing is exercised in a real browser on one element (the login button) with four mutation kinds; the evaluation over 30 mutations is a later slice.
- Selenium runs are supported by the generated `conftest.py` and the plugin, but were exercised only with a fake driver; the Selenium conftest cannot intercept requests, so only the base-URL check protects it.
- Parallel workers are tested with a fake browser; speed-up (NFR-23) has not been measured.
- Video and Playwright trace capture (FR-18, optional) are not implemented.
- Results record the final attempt of each test; per-attempt history is kept only in the raw result lines and JUnit files.
- Only the checks named above guard the browser; there is no network-level sandbox.
