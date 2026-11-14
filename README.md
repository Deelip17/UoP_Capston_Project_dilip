# AI-Powered Test Automation Framework for Enterprise Software Quality Assurance

MSIT Capstone Project, University of the People. A working **prototype** of an AI-assisted quality-assurance pipeline, evaluated on public demonstration web applications only.

> **Status:** Unit 3 baseline: architecture, requirements and Git strategy are documented; implementation starts in Units 4–5. No source code has been written yet.

## What the framework will do

Requirement text → **Requirement Analyzer** → **Test Case Generator** → **Script Generator** → **Execution Engine** ⇄ **Self-Healing Engine** → **Failure Analyzer** → **Reporting Engine** → **Dashboard**, supported by a Data Masking and Validation Layer, SQLite Persistence, Audit Logging and a single LLM Gateway. Two human approval gates keep a person in control of test scope and permanent locator changes.

Technology: Python 3.12, Playwright, Selenium, PyTest, OpenAI API, SQLite, Pandas, GitHub, GitHub Actions.

## Repository layout

| Folder | Contents |
|---|---|
| `src/aitaf/` | Source code: one package per module plus a shared `core` (placeholder until Unit 5) |
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
| `.github/` | Pull-request template (workflows added in Unit 4) |

## Branching

`main` holds reviewed, tagged work. `develop` integrates completed work. Changes are made on short-lived `feature/*`, `docs/*`, `fix/*` branches and merged by pull request. See [docs/project-management/GIT_STRATEGY.md](docs/project-management/GIT_STRATEGY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation map

- Requirements: [Functional](docs/requirements/FUNCTIONAL_REQUIREMENTS.md), [Non-functional](docs/requirements/NON_FUNCTIONAL_REQUIREMENTS.md)
- Design: [System architecture](docs/architecture/01_SYSTEM_ARCHITECTURE.md), [Component architecture](docs/architecture/02_COMPONENT_ARCHITECTURE.md), [Data flow](docs/architecture/05_DATA_FLOW.md), [Sequence flow](docs/architecture/06_SEQUENCE_FLOW.md)

## Licence and confidentiality

Academic coursework; licence to be decided. This repository contains no client names, client data or secrets, and is tested only against public demonstration applications.
