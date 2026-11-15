# AI-Powered Test Automation Framework for Enterprise Software Quality Assurance

MSIT Capstone Project, University of the People. A working **prototype** of an AI-assisted quality-assurance pipeline, evaluated on public demonstration web applications only.

> **Status:** Unit 5 core implemented and released as [v0.5.0](https://github.com/Deelip17/UoP_Capston_Project_dilip/releases/tag/v0.5.0). Four of the eight modules work (Requirement Analyzer, Test Case Generator, Script Generator, a Self-Healing core) with masking, an LLM Gateway, SQLite persistence and metrics. **All LLM output so far comes from a deterministic mock provider; no live model has been called.** The Execution Engine, Failure Analyzer, Reporting Engine and Dashboard are not built yet (Units 6 and 7). What is and is not shown: [docs/project-management/UNIT5_HANDOFF.md](docs/project-management/UNIT5_HANDOFF.md).

## What the framework will do

Requirement text → **Requirement Analyzer** → **Test Case Generator** → **Script Generator** → **Execution Engine** ⇄ **Self-Healing Engine** → **Failure Analyzer** → **Reporting Engine** → **Dashboard**, supported by a Data Masking and Validation Layer, SQLite Persistence, Audit Logging and a single LLM Gateway. Two human approval gates keep a person in control of test scope and permanent locator changes.

Technology: Python 3.12, Playwright, Selenium, PyTest, OpenAI API, SQLite, Pandas, GitHub, GitHub Actions.

## Repository layout

| Folder | Contents |
|---|---|
| `src/aitaf/` | Source code: `analyzer`, `generator`, `scriptgen`, `healing`, a shared `core` and CI tooling in `quality`; each package has a README |
| `tests/` | Unit, integration and end-to-end tests |
| `prompts/` | Versioned LLM prompt templates |
| `sample-apps/` | Local demonstration application used as the system under test |
| `evaluation/` | Evaluation scripts, mutation catalogue, labelled data (Unit 6) |
| `docs/architecture/` | **Design files:** architecture, component, data-flow, sequence, security and CI/CD design, with diagrams |
| `docs/requirements/` | Functional and non-functional requirements |
| `docs/project-management/` | Git strategy, schedule, risk register |
| `docs/adr/` | Architecture decision records |
| `evidence/` | Screenshots and logs with an evidence register |
| `scripts/` | Developer helper scripts |
| `.github/` | Pull-request template and the workflows `ci.yml` (checks on every push) and `release.yml` (GitHub Release on a `v*` tag) |

## Try it (mock provider, no API key needed)

```
python -m venv .venv
.venv\Scripts\activate            # Windows; on Linux or macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e . --no-deps
python -m aitaf analyze --input data/requirements/sample_requirements.md --db demo.db
python -m aitaf generate --db demo.db
python -m aitaf review --db demo.db --list
python -m aitaf review --db demo.db --approve <TC-ID from the list>
python -m aitaf script --db demo.db --out-dir generated_tests
python -m aitaf metrics --db demo.db
python -m aitaf heal --before data/dom/login_before.html --after data/dom/login_all_changed.html --primary id=login-button --fallback "css=button[type=submit]"
pytest
```

`run`, `execute`, `diagnose` and `report` are placeholders that exit with code 3. Setup details, including an optional API key, are in [docs/user-guide/SETUP.md](docs/user-guide/SETUP.md).

## Branching

`main` holds reviewed, tagged work. `develop` integrates completed work. Changes are made on short-lived `feature/*`, `docs/*`, `fix/*` branches and merged by pull request. See [docs/project-management/GIT_STRATEGY.md](docs/project-management/GIT_STRATEGY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation map

- Requirements: [Functional](docs/requirements/FUNCTIONAL_REQUIREMENTS.md), [Non-functional](docs/requirements/NON_FUNCTIONAL_REQUIREMENTS.md)
- Design: [System architecture](docs/architecture/01_SYSTEM_ARCHITECTURE.md), [Component architecture](docs/architecture/02_COMPONENT_ARCHITECTURE.md), [Data flow](docs/architecture/05_DATA_FLOW.md), [Sequence flow](docs/architecture/06_SEQUENCE_FLOW.md)

## Licence and confidentiality

Academic coursework; licence to be decided. This repository contains no client names, client data or secrets, and is tested only against public demonstration applications.
