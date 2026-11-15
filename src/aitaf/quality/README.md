# quality (developer and release tooling)

Small command-line tools run from CI. They are not part of the test-automation pipeline and are exempt from the component import rules.

| Tool | Command | Purpose | Requirements |
|---|---|---|---|
| Import rules | `python -m aitaf.quality.import_rules [ROOT]` | Fails on a component importing another component, `core` importing a component, vendor imports outside their owner (`openai` only in `core/llm`, `sqlite3` only in `core/storage`, Playwright and Selenium only in the Execution Engine package), and relative imports that climb out of a package | NFR-17 |
| Release notes | `python -m aitaf.quality.release notes CHANGELOG.md vX.Y.Z` | Prints the changelog section used as the GitHub Release body | Git strategy, ADR-033 |
| Tag check | `python -m aitaf.quality.release check vX.Y.Z` | Refuses a tag that does not equal `aitaf.__version__` | Git strategy |

`ci.yml` runs the import-rule check on every push; `release.yml` runs all three before publishing a release.

## Tests

`tests/unit/quality/`. The import-rule test also runs the check on the real source tree and expects zero violations; the release tests check the workflow files for least privilege, first-party actions only and the expected steps.

## Not built

- The import-rule check covers imports, not data flow: it cannot show that components exchange records only through persistence.
- `release.yml` publishes a release for a pushed tag; creating the tag, and a release page for the earlier `v0.1.0` tag, are manual steps.
