# Changelog

Format: Keep a Changelog. Versions follow Semantic Versioning.

## [Unreleased]

### Added
- Repository skeleton, README, contributing guide and pull-request template.
- Architecture, requirements and Git strategy documentation (Unit 3 baseline).
- Unit 4 CI workflow (`.github/workflows/ci.yml`): lint, test matrix (Ubuntu, Windows), security audit, build.
- Unit 5 slice 1 thin core: `aitaf.core.errors`, `aitaf.core.config`, `aitaf.core.logging`, `aitaf.core.models` (AnalyzedRequirement, TestCase) with 31 unit tests at 98% coverage. Pydantic 2.14.3 added as a runtime dependency (ADR-032). Pytest `blackbox` and `whitebox` markers added for Unit 5 evidence.
- Unit 5 slice 2: SQLite persistence behind a repository interface with versioned migrations and an in-memory fake (`aitaf.core.storage`); LLM Gateway with provider interface, deterministic mock provider, per-run call cap, mock fallback and one audit record per call (`aitaf.core.llm`); `aitaf` command-line skeleton driven by a JSON configuration file. 82 tests at 97% coverage.
- Unit 5 slice 3: Data Masking and Validation Layer (`aitaf.core.masking`: secret and personal-data redaction, input sanitising with injection screening, LLM-output schema validation) and Requirement Analyzer (`aitaf.analyzer`: plain/Markdown/user-story intake, versioned prompt, deterministic IDs, combined risk rating, ambiguity flags). `aitaf analyze` command, synthetic sample requirements in `data/requirements/`, requirements persisted (schema migration 2). 156 tests at 98% coverage.
- Unit 5 slice 4: Test Case Generator (`aitaf.generator`): positive, negative and boundary scenarios, complete traceable test cases, synthetic data with a personal-data check, near-duplicate removal, coverage-gap report, human review gate, and JSON/CSV/Markdown export and re-import. `aitaf generate` and `aitaf review` commands; test cases, scenarios and data persisted (schema migration 3); `TestCase` now carries model and prompt version. 215 tests at 98% coverage.
- Unit 5 slice 5: Script Generator (`aitaf.scriptgen`): structured automation plans rendered by templates into PyTest scripts, page objects and a per-page locator repository for Playwright and Selenium, locators with primary and ordered fallback strategies, AST allow-list static validation (imports, builtins, attributes, URL hosts, secrets) before anything is saved, confined file writes, manifest. `aitaf script` command (Approved cases only unless `--no-review`); scripts and locators persisted (schema migration 4). 297 tests at 97% coverage.
- Unit 5 slice 6: Self-Healing core (`aitaf.healing`, interface in `aitaf.core.healing`): failure classification (locator failure versus application defect), cost-ordered repair ladder (stored fallbacks, DOM-similarity matching, optional LLM suggestion), candidate validation on role, text, context and action fit, bounded attempts, proposed healing events with a human approval gate before any permanent locator change, success rates. DOM snapshot parser and locator resolver, fixtures in `data/dom/`, `aitaf heal` demonstration command; healing events persisted (schema migration 5). 481 tests at 98% coverage.
