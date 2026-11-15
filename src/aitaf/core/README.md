# core

Shared foundation that every other package depends on. Components import `core`, never each other (NFR-17, checked in CI by `python -m aitaf.quality.import_rules`).

| Module | Purpose | Requirements |
|---|---|---|
| `config` | Immutable settings from environment variables or a JSON file; the API key is accepted from the environment only | FR-35, NFR-09 |
| `errors` | One exception hierarchy rooted at `AitafError` | NFR-10 |
| `logging` | JSON log lines carrying a run ID (a context variable) | NFR-34 |
| `models` | Frozen pydantic records exchanged between modules, each AI artefact labelled with model and prompt version | FR-34, NFR-22, NFR-30 |
| `masking/` | Data Masking and Validation Layer: redaction of secrets and personal data, input sanitising with prompt-injection screening, schema validation of LLM output | FR-02, FR-30, NFR-10, NFR-13, NFR-15 |
| `llm/` | LLM Gateway (call cap, mock fallback, one audit record per call), provider interface, deterministic mock provider | FR-36, FR-37, NFR-25, ADR-026 |
| `storage/` | Repository interface, in-memory fake and SQLite implementation with versioned migrations (currently 6) | FR-19, NFR-07, NFR-24 |
| `metrics` | Timers, outcome counters, token and cost samples written per run | NFR-35 |
| `healing` | `LocatorHealer` interface and the failure-context and result types, so the Execution Engine can call a healer without importing it | FR-22 to FR-24, NFR-17 |

## Public API

`Settings.from_env()` / `Settings.from_file()`, `mask()`, `sanitize_requirement_text()`, `validate_llm_json()`, `LlmGateway`, `MockProvider`, `SqliteRepository`, `InMemoryRepository`, `Metrics`, the records in `models`.

## Tests

`tests/unit/core/` and `tests/unit/masking/`. The repository contract tests run against both the in-memory fake and a real SQLite file, including a process-kill test of durability.

## Not built

- No OpenAI provider yet: only the mock provider exists, so no live model output has ever been produced. Retry with back-off (NFR-06) is therefore also missing.
- Masking is rule-based (emails, keys, tokens, card, ID and phone patterns). It does not detect personal names or addresses.
- Nothing writes test results (`test_results` table, FR-19) until the Execution Engine exists.
