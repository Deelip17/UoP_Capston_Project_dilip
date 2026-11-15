# Changelog

Format: Keep a Changelog. Versions follow Semantic Versioning.

## [Unreleased]

### Added
- Unit 6 planning: `docs/project-management/UNIT6_PLAN.md` (decisions, artefact checklist, evaluation design, slices U6-0 to U6-11, three-session workflow) and `docs/project-management/EVIDENCE_SESSION_BRIEF.md` (instructions for the screenshot-only session); Unit 5 screenshots registered (E04 to E17b).
- Unit 5 slice 8: a README for every top-level package (each with a "Not built" section), documentation tests, the Unit 5 handoff document for writing the paper (`docs/project-management/UNIT5_HANDOFF.md`) an updated top-level README with a quick start, and a screenshot guide with the assignment coverage matrix and the Cowork prompt (`docs/project-management/UNIT5_SCREENSHOT_GUIDE.md`).

## [0.5.0] - 2026-11-14

### Added
- Unit 5 slice 4: Test Case Generator (`aitaf.generator`): positive, negative and boundary scenarios, complete traceable test cases, synthetic data with a personal-data check, near-duplicate removal, coverage-gap report, human review gate, and JSON/CSV/Markdown export and re-import. `aitaf generate` and `aitaf review` commands; test cases, scenarios and data persisted (schema migration 3); `TestCase` now carries model and prompt version. 215 tests at 98% coverage.
- Unit 5 slice 5: Script Generator (`aitaf.scriptgen`): structured automation plans rendered by templates into PyTest scripts, page objects and a per-page locator repository for Playwright and Selenium, locators with primary and ordered fallback strategies, AST allow-list static validation (imports, builtins, attributes, URL hosts, secrets) before anything is saved, confined file writes, manifest. `aitaf script` command (Approved cases only unless `--no-review`); scripts and locators persisted (schema migration 4). 297 tests at 97% coverage.
- Unit 5 slice 6: Self-Healing core (`aitaf.healing`, interface in `aitaf.core.healing`): failure classification (locator failure versus application defect), cost-ordered repair ladder (stored fallbacks, DOM-similarity matching, optional LLM suggestion), candidate validation on role, text, context and action fit, bounded attempts, proposed healing events with a human approval gate before any permanent locator change, success rates. DOM snapshot parser and locator resolver, fixtures in `data/dom/`, `aitaf heal` demonstration command; healing events persisted (schema migration 5). 481 tests at 98% coverage.
- Unit 5 slice 7: metrics hooks (`aitaf.core.metrics`): timers, outcome counters, token and cost logging written per run to persistence (schema migration 6) from the LLM gateway, Requirement Analyzer, Test Case Generator, Script Generator and Self-Healing Engine; configurable token prices (`LLM_PRICE_IN_PER_1K`, `LLM_PRICE_OUT_PER_1K`); `aitaf metrics` command. Automated import-rule check for NFR-17 (`aitaf.quality.import_rules`) added to CI. Release workflow (`.github/workflows/release.yml`) that re-verifies, builds the wheel and an evidence bundle and publishes a GitHub Release with notes from this changelog. The package version is now read from `aitaf.__version__`.

## [0.1.0] - 2026-11-14

### Added
- Repository skeleton, README, contributing guide and pull-request template.
- Architecture, requirements and Git strategy documentation (Unit 3 baseline).
- Unit 4 CI workflow (`.github/workflows/ci.yml`): lint, test matrix (Ubuntu, Windows), security audit, build.
- Unit 5 slice 1 thin core: `aitaf.core.errors`, `aitaf.core.config`, `aitaf.core.logging`, `aitaf.core.models` (AnalyzedRequirement, TestCase) with 31 unit tests at 98% coverage. Pydantic 2.14.3 added as a runtime dependency (ADR-032). Pytest `blackbox` and `whitebox` markers added for Unit 5 evidence.
- Unit 5 slice 2: SQLite persistence behind a repository interface with versioned migrations and an in-memory fake (`aitaf.core.storage`); LLM Gateway with provider interface, deterministic mock provider, per-run call cap, mock fallback and one audit record per call (`aitaf.core.llm`); `aitaf` command-line skeleton driven by a JSON configuration file. 82 tests at 97% coverage.
- Unit 5 slice 3: Data Masking and Validation Layer (`aitaf.core.masking`: secret and personal-data redaction, input sanitising with injection screening, LLM-output schema validation) and Requirement Analyzer (`aitaf.analyzer`: plain/Markdown/user-story intake, versioned prompt, deterministic IDs, combined risk rating, ambiguity flags). `aitaf analyze` command, synthetic sample requirements in `data/requirements/`, requirements persisted (schema migration 2). 156 tests at 98% coverage.
