# scriptgen (Script Generator)

Compiles approved test cases into executable, maintainable PyTest scripts for Playwright or Selenium, with locators held in one place and static safeguards because generated code is untrusted (FR-12 to FR-16).

The model never writes code. For each case it returns a structured plan (page, named locators each with a primary and ordered fallback strategies, and steps from a fixed vocabulary: open, click, type, select, assert_text, assert_visible). Python templates render the files; names are restricted to simple identifiers by the schema.

Output under the chosen directory: `conftest.py`, `tests/test_<case>.py`, `pages/<page>_page.py` (page object that tries the primary locator, then each fallback), `locators/<page>_locators.py` (the only place selectors appear), and `manifest.json`.

Every generated file is checked by an AST allow-list before anything is written (imports, dangerous builtins and attributes, URL hosts, hard-coded secrets and personal data). A script that fails is rejected with reasons and not saved. Writes are confined to the output directory. The base URL host must be on the allow-list.

| Module | Purpose | Requirements |
|---|---|---|
| `generator` | `ScriptGenerator`, `ScriptGenerationResult` | FR-12, FR-13, FR-14, FR-16, FR-30 |
| `validator` | `validate_script`, `assert_valid` (AST allow-list) | FR-15, NFR-11 |
| `plan`, `templates`, `prompts` | Plan schema, Playwright and Selenium templates, versioned prompts `sg-v1` (no page context) and `sg-v2` (with a page catalogue) | FR-14, NFR-10, NFR-22 |
| `catalogue` | `PageCatalogue`: the elements of the application's baseline HTML snapshots (id, class, test hook, text), the prompt block, and `check_plan`, which rejects a plan that names anything not on the pages | FR-12, FR-14, FR-16, NFR-10 |
| `files` | `safe_write` | NFR-11 |
| `mock_responder` | Deterministic stand-in for the model | FR-36 |

## Public API

`ScriptGenerator(gateway, repo, framework, base_url, allowed_hosts, output_dir, metrics=None).generate(cases, test_data)`; CLI: `aitaf script [--framework playwright|selenium] [--base-url URL] [--allow-host HOST] [--no-review] [--pages DIR]`. `ScriptGenerator(..., catalogue=PageCatalogue.from_snapshots(DIR))` or `--pages DIR` gives the model the page catalogue (prompt `sg-v2`): it may use only listed elements, a plan with an invented selector or page path is asked again once and then rejected (nothing saved), and all locators of a script sit on one page object named after the directory. An optional `flow.txt` in the directory lists the pages in the order a user meets them (the mock uses it to reach a page).

## Tests

`tests/unit/scriptgen/`. Forbidden-construct fixtures are rejected; generated test functions are run against fake Playwright and Selenium drivers to check that fallback locators are tried in order.

## Not built

- Selenium scripts are still only run against a fake driver.
- The catalogue lists elements that have an id or a test hook; elements without either cannot be targeted. Page structure beyond the flow order, and login state, are not described to the model.
- Credentials never go into a prompt or a generated file (masking and the static validator forbid it); a script that needs a real login therefore needs an environment where sign-in is open (the sample shop's `--open-login`).
- The mock plans pages by keyword overlap and a fixed rule for reaching a page; it shows the plumbing, not the quality of a real model. Live plans are measured in the evaluation (U6-8).
