# Progress Log

Written as work happens. It is the source for the progress documentation and for Parts A and B of the Unit 5 report, so record only what actually occurred.

## Slice log

| Date | Unit | Slice | Requirements | Commit | Tests (total, black-box, white-box) | Coverage | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|
| 2026-11-14 | 4 | CI pipeline and scaffold | NFR-12, NFR-18, NFR-19, NFR-26 | 7283c13 | 1 smoke test | 100% | E03a-E03e | CI run 4 on `develop` green |
| 2026-11-14 | 5 | Slice 1 thin core: `core/__init__`, `core/errors`, `core/config`, `core/logging`, `core/models` | NFR-09, NFR-10, NFR-17, NFR-22, NFR-30, NFR-34, FR-04, FR-10, FR-34, FR-35, FR-37, ADR-026, ADR-032 | (this commit) | 31 (21 blackbox, 10 whitebox) | 98.4% | none (no demo logic yet) | Pydantic 2.14.3 adopted (ADR-032); pytest markers added; `TestCase` model excluded from pytest collection via `__test__=False` |
| 2026-11-14 | 5 | Slice 2: `core/storage` (repository, in-memory fake, SQLite with migrations), `core/llm` (provider interface, mock provider, gateway with cap, fallback and audit), `cli`, config file loading | FR-19, FR-35, FR-36, FR-37, NFR-07, NFR-14, NFR-24, NFR-25, ADR-026 | (this commit) | 82 (55 blackbox, 27 whitebox) | 97% | none (CLI stages not implemented yet) | Repository contract tests run against both fake and SQLite; kill-process test verifies integrity check and incomplete run. OpenAI provider and retry with back-off (NFR-06) deferred to the slice that first needs a live call |
| 2026-11-14 | 5 | Slice 3: `core/masking` (masking, input validation, LLM-output schema validation), `analyzer` (intake, versioned prompt, mock responder, Requirement Analyzer), `requirements` table (migration 2), `aitaf analyze` command, sample data | FR-01, FR-02, FR-03, FR-04, FR-05, FR-30, FR-35, NFR-10, NFR-13, NFR-15, NFR-17, NFR-22, NFR-30 | (this commit) | 156 (114 blackbox, 42 whitebox) | 98% | E04 (log), E17a (pytest log) | Seeded secrets never reach the provider; injection fixtures rejected before any LLM call; invalid model output re-asked once then rejected. Tag `v0.1.0` after CI green |

## Issues found by tests (Part B)

Record each real failure: what failed, cause, fix, commit.

| Date | Test | Symptom | Cause | Fix | Commit |
|---|---|---|---|---|---|
| 2026-11-14 | deliberate demo test (E03b) | CI red: tests failed and ruff B011 flagged `assert False` | Intentional failing test | Removed the test | 7912566 |
| 2026-11-14 | `test_settings_are_immutable`, `test_analyzed_requirement_is_frozen` | Ruff B017 "do not assert blind `Exception`" failed the lint gate | Tests used `pytest.raises(Exception)` for pydantic frozen-model assignment | Tightened to `pytest.raises(PydanticValidationError)`, which is what pydantic actually raises for frozen models | (this commit) |
| 2026-11-14 | `test_invalid_config_is_rejected_with_clear_message` | CI run 7 red on Ubuntu and Windows while the same test passed locally | CI sets `LLM_PROVIDER=mock`; the environment overrides the config file by design, so the invalid file value was never read. The test was not isolated from the environment | Added an autouse fixture that clears the framework's environment variables for CLI tests; reproduced locally with `LLM_PROVIDER=mock pytest -n auto` | (this commit) |
| 2026-11-14 | `test_analyze_command_runs_on_sample_and_reports` | `aitaf analyze` exited 1 with "no run ID is set" on the sample file | The CLI called `new_run_id()`, which only generates an ID; it never bound it to the run context the gateway reads. The analyzer unit tests bound it through a fixture, so only the end-to-end CLI test exposed the gap | Added `set_run_id(run_id)` in the CLI right after creating the run | (this commit) |

## Challenges and resolutions (Part A)

| Date | Challenge | How it was resolved |
|---|---|---|
| 2026-11-14 | The domain model class `TestCase` triggered pytest collection warnings because its name matches the test-class pattern | Added a class variable `__test__: ClassVar[bool] = False` on the pydantic model so pytest skips it without renaming the domain concept |
| 2026-11-14 | Ruff rule UP042 rejected `class RiskLevel(str, Enum)` on Python 3.12 | Switched both enums to `enum.StrEnum` which is the Python 3.11+ idiom |
| 2026-11-14 | The pipeline must complete offline and deterministically (FR-36) but the mock provider returned only a generic JSON stub that fails the analyzer's schema | Gave the mock provider per-component responders; the analyzer registers a rule-based extractor that returns schema-valid JSON, and the analyzer's own keyword risk rules are what the tests exercise |
| 2026-11-14 | Requirement text is untrusted and shares the prompt with instructions (NFR-13) | Fixed delimiters plus an instruction hierarchy in a versioned prompt, injection screening that rejects before any LLM call, masking before the call, and schema validation of the reply with one re-ask |

## Milestones, tags and releases (Part C)

| Date | Tag | Branch | Release | Contents |
|---|---|---|---|---|
| 2026-11-14 | v0.1.0 | develop | tag only (GitHub Release planned at v0.5.0) | Core, persistence, LLM gateway, masking layer, Requirement Analyzer; 156 tests, 98% coverage, CI run 9 green (commit f31a76d) |
