# analyzer (Requirement Analyzer)

Turns raw requirements into structured, identified, risk-rated records and stops poor requirements early (FR-01 to FR-05).

Per requirement: split and read the input (plain text, Markdown or user stories) -> sanitise (size, encoding, control characters, injection screening; failures are rejected before any LLM call) -> mask secrets and personal data -> one versioned prompt through the LLM Gateway -> schema validation of the reply (one re-ask, then rejection) -> deterministic ID from source reference and content hash -> risk rating (the higher of the model's rating and a keyword rule, with a stored rationale) -> ambiguity flags -> persist.

| Module | Purpose | Requirements |
|---|---|---|
| `intake` | `load_requirements`, `parse_requirements`, `detect_format` | FR-01 |
| `analyzer` | `RequirementAnalyzer`, `AnalysisResult` (ready, flagged, rejected) | FR-02 to FR-05, FR-30, NFR-13 |
| `prompts` | Versioned prompt `ra-v1` with delimited, untrusted input | NFR-22, NFR-13 |
| `mock_responder` | Deterministic stand-in for the model, used by the mock provider | FR-36 |

Flagged requirements are excluded from test generation until clarified (FR-05).

## Public API

`RequirementAnalyzer(gateway, repo, metrics=None).analyze(items) -> AnalysisResult`; CLI: `aitaf analyze --input FILE`.

## Tests

`tests/unit/analyzer/`, plus the end-to-end CLI and metrics pipeline tests. Sample inputs are synthetic and live in `data/requirements/`.

## Not built

- All output so far comes from the mock provider; the quality of a real model's extraction, risk rating and ambiguity detection has not been measured.
- Ambiguity detection uses a fixed list of vague words and an "always and never" rule, not language understanding.
