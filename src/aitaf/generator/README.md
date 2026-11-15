# generator (Test Case Generator)

Produces traceable test scenarios, test cases and synthetic data from analysed requirements, and leaves approval to a person (FR-05 to FR-11).

Per eligible requirement (not flagged as ambiguous): mask the requirement record -> one versioned prompt `tg-v1` through the gateway returning positive, negative and boundary scenarios with cases and suggested data -> schema validation (a missing scenario type counts as invalid; one re-ask) -> labelled records with deterministic IDs -> data check (model-suggested values that look like real personal data are replaced by synthetic ones) -> near-duplicate removal across all cases -> coverage-gap report for the roles named in the requirements -> persist. New cases start `Pending`.

| Module | Purpose | Requirements |
|---|---|---|
| `generator` | `TestCaseGenerator`, `GenerationResult` | FR-06 to FR-09, NFR-30, NFR-32 |
| `review` | `set_review_status`, `cases_for_scripting` (the human gate) | FR-10, NFR-31 |
| `export` | `export_cases`, `import_cases` for JSON, CSV and Markdown | FR-11 |
| `synthetic` | Rule-based synthetic values by field name | FR-08 |
| `prompts`, `mock_responder` | Versioned prompt and deterministic stand-in | NFR-22, FR-36 |

In review mode only `Approved` cases are scripted; `Rejected` cases never are. Every status change is logged.

## Public API

`TestCaseGenerator(gateway, repo, metrics=None).generate(requirements)`; CLI: `aitaf generate [--export-dir DIR]`, `aitaf review --list|--approve ID|--reject ID`.

## Tests

`tests/unit/generator/`, plus the CLI tests. Seeded duplicates, seeded real-looking data and exports with awkward text are covered.

## Not built

- All output so far comes from the mock provider; the quality and coverage of a real model's test design has not been evaluated (NFR-32 coverage review is reported per run but not yet assessed).
- Only roles are checked for coverage; locales named in requirements are not.
- The Orchestrator that would enforce the review gate inside a full `aitaf run` does not exist; the gate is enforced by `aitaf script` and `cases_for_scripting`.
