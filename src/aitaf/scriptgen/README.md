# scriptgen (Script Generator)

Compiles approved test cases into executable, maintainable PyTest scripts for Playwright or Selenium, with locators held in one place and static safeguards because generated code is untrusted (FR-12 to FR-16).

The model never writes code. For each case it returns a structured plan (page, named locators each with a primary and ordered fallback strategies, and steps from a fixed vocabulary: open, click, type, select, assert_text, assert_visible). Python templates render the files; names are restricted to simple identifiers by the schema.

Output under the chosen directory: `conftest.py`, `tests/test_<case>.py`, `pages/<page>_page.py` (page object that tries the primary locator, then each fallback), `locators/<page>_locators.py` (the only place selectors appear), and `manifest.json`.

Every generated file is checked by an AST allow-list before anything is written (imports, dangerous builtins and attributes, URL hosts, hard-coded secrets and personal data). A script that fails is rejected with reasons and not saved. Writes are confined to the output directory. The base URL host must be on the allow-list.

| Module | Purpose | Requirements |
|---|---|---|
| `generator` | `ScriptGenerator`, `ScriptGenerationResult` | FR-12, FR-13, FR-14, FR-16, FR-30 |
| `validator` | `validate_script`, `assert_valid` (AST allow-list) | FR-15, NFR-11 |
| `plan`, `templates`, `prompts` | Plan schema, Playwright and Selenium templates, versioned prompt `sg-v1` | FR-14, NFR-10, NFR-22 |
| `files` | `safe_write` | NFR-11 |
| `mock_responder` | Deterministic stand-in for the model | FR-36 |

## Public API

`ScriptGenerator(gateway, repo, framework, base_url, allowed_hosts, output_dir, metrics=None).generate(cases, test_data)`; CLI: `aitaf script [--framework playwright|selenium] [--base-url URL] [--allow-host HOST] [--no-review]`.

## Tests

`tests/unit/scriptgen/`. Forbidden-construct fixtures are rejected; generated test functions are run against fake Playwright and Selenium drivers to check that fallback locators are tried in order.

## Not built

- The generated scripts have never been executed in a real browser or against a sample application: that needs the Execution Engine and the sample app (FR-12 and FR-13 acceptance is only partly shown).
- One page per test case; flows across several pages are not planned yet.
- All plans so far come from the mock provider.
