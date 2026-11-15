# healing (Self-Healing Engine)

Repairs broken locators during execution without hiding real defects (FR-22 to FR-26). It works on an HTML snapshot taken at the moment of failure, so it needs no browser. The Execution Engine will call it through the `LocatorHealer` interface in `core`.

Ladder, cheapest first:

1. **Classify** (`classify`): only locator failures (element not found, stale, not interactable) enter the ladder. An assertion failure is an application defect and is returned unchanged; unknown failures are left alone.
2. **Stored fallbacks**: try the locator's fallback strategies against the snapshot.
3. **DOM similarity** (`similarity`): score elements on tag, attributes, visible text, and context (ancestor path and neighbouring text); take the best above a threshold.
4. **LLM suggestion** (`llm_step`): off by default; only reached after steps 2 and 3 fail; sees a short, masked, injection-screened list of candidates and must return a schema-valid locator.

Every candidate, from any rung, is **validated** (`validate`): same role, similar text, same context, and suitable for the step's action. A present-but-wrong element is rejected and the step still fails. A proposed locator must resolve to exactly the chosen element, or a unique one is derived (`locators`).

Every attempt is stored as a proposed, unapproved `HealingEvent`. A permanent change to the locator repository needs human approval (`approval`). Attempts are limited per step and per run.

| Module | Purpose | Requirements |
|---|---|---|
| `engine` | `SelfHealingEngine`, `HealingConfig` | FR-22 to FR-24, FR-26, NFR-03 |
| `dom`, `resolver`, `signature` | Snapshot parser, CSS/XPath-subset resolver, expected-element signature | FR-23 |
| `approval`, `metrics` | `approve_healing_event`, `success_rates` | FR-25, FR-26 |

## Public API

`SelfHealingEngine(repo, config=None, gateway=None, metrics=None).heal(FailureContext) -> HealResult`; CLI demonstration: `aitaf heal --before FILE --after FILE --primary KIND=VALUE [--fallback KIND=VALUE] [--llm]`. Fixtures are in `data/dom/`.

## Tests

`tests/unit/healing/`. Healing modules are covered at 93 to 100% (NFR-18 asks 90%).

## Not built

- Not connected to a live Execution Engine, a real browser or the sample application; it has only been run on six hand-made DOM fixtures.
- The seeded mutation harness (FR-38) and the healing success rate on it (FR-39) do not exist, so the thresholds (0.6 similarity, 0.5 text, 0.3 context) are initial values, and NFR-03 (repair within 3 s, LLM repair within 30 s) is not yet measured on a mutation catalogue.
- Approving a healing event is available through the Python API only; there is no CLI command or report page for it yet.
- The CSS and XPath resolver supports a subset; other selectors are skipped, not guessed.
- The LLM rung has only run against the mock provider.
