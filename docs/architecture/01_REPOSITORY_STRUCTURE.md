# 01 — Repository Structure

**Status:** Draft v0.2 (aligned with `MASTER_PLAN.md` v1.1 and `PROJECT_ROADMAP.md`; design only, no code) · **Feeds:** Unit 3 AA (Q2), Report §3.2 (Git, CI/CD, tools) and §4.1 (official numbering)

## 1. Executive Summary

Two distinct trees exist and must not be confused:

| Tree | Purpose | Location |
|---|---|---|
| **Academic workspace** (this folder) | Course instructions, knowledge base, report chapters, rubrics, evidence | `Capstone_Full_Project/` |
| **Framework repository** (GitHub) | The deliverable software, its tests, docs, CI/CD | `UoP_Capston_Project_dilip/` (GitHub repository) |

The framework repository is **modular by component**: one Python package per approved architecture component, each with its own unit tests and README (CLAUDE.md rule: modular, tested, documented, evidence-producing). Academic documents are mirrored into the repo under `docs/` so the Unit 3 grader sees source code, documentation and design files organised together (Unit 3 AA Q2b).

## 2. Framework Repository Layout (target)

```text
UoP_Capston_Project_dilip/
├── README.md                      # Overview, quick start, badges, architecture image
├── LICENSE
├── CONTRIBUTING.md                # Branching, commit convention, PR checklist
├── CHANGELOG.md                   # Keep-a-Changelog format, one entry per release tag
├── pyproject.toml                 # Package metadata, tool config (ruff, pytest, coverage)
├── requirements.txt               # Runtime deps (pinned; includes pandas for metrics)
├── requirements-dev.txt           # Test/lint deps (pinned)
├── Dockerfile                     # Deployment/configuration (Unit 6 Part C; roadmap M13, E15)
├── docker-compose.yml             # Framework + sample app
├── .env.example                   # Variable NAMES only; never real secrets
├── .gitignore                     # .env, *.db, evidence/raw, __pycache__, .venv
├── .pre-commit-config.yaml        # Lint, format, secret scan
├── .github/
│   ├── workflows/                 # See 08_CICD_DESIGN.md
│   │   ├── ci.yml
│   │   ├── integration.yml
│   │   ├── nightly-e2e.yml
│   │   ├── security.yml
│   │   └── release.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/
│   ├── CODEOWNERS
│   └── dependabot.yml
├── src/
│   └── aitaf/                     # "AI Test Automation Framework" root package
│       ├── __init__.py
│       ├── core/                  # Shared kernel (no business logic)
│       │   ├── config/            #   typed settings, env loading
│       │   ├── models/            #   dataclasses/pydantic: Requirement, TestCase, Script, Run, Failure…
│       │   ├── llm/               #   OpenAI client wrapper, prompt registry, cache, retry, mock provider
│       │   ├── masking/           #   Data Masking and Validation Layer (redaction, schema validation)
│       │   ├── metrics/           #   timers/counters/hooks (needed from Unit 5; roadmap critical path)
│       │   ├── storage/           #   SQLite repository layer + migrations
│       │   ├── logging/           #   structured logging, Audit Logging
│       │   └── errors.py
│       ├── requirement_analyzer/  # Component 1
│       ├── test_case_generator/   # Component 2
│       ├── script_generator/      # Component 3 (Playwright + Selenium adapters)
│       ├── execution_engine/      # Component 4 (PyTest runner, evidence capture)
│       ├── self_healing/          # Component 5 (locator repair)
│       ├── failure_analyzer/      # Component 6
│       ├── reporting/             # Component 7 (HTML, Markdown, PDF, metrics computation)
│       ├── dashboard/             # Component 8 (static HTML dashboard over metrics)
│       ├── orchestrator/          # Pipeline coordinator + CLI entry point
│       └── cli.py
├── prompts/                       # Versioned prompt templates (text/YAML), reviewed like code
├── tests/
│   ├── unit/                      # Mirrors src/aitaf/ one-to-one; LLM mocked
│   ├── integration/               # Component pairs and full pipeline against demo app
│   ├── e2e/                       # Pipeline against public demo web apps
│   ├── fixtures/                  # Sample requirements, HTML pages, recorded LLM responses
│   └── conftest.py
├── sample-apps/                   # Local demo SUT (static HTML with deliberately mutable locators)
├── evaluation/                    # Unit 6: seeded locator-mutation catalogue, hand-labelled failure set,
│                                  #   evaluation scripts, raw CSVs (Appendix B; MASTER_PLAN 9.5)
├── data/
│   ├── requirements/              # Sample requirement inputs (public/synthetic only)
│   └── db/                        # SQLite file location (git-ignored; schema in src)
├── GLOSSARY.md                    # Terminology lock: canonical component/metric names (MASTER_PLAN 9.1)
├── docs/
│   ├── architecture/              # Mirrors Capstone_Full_Project/architecture/
│   ├── requirements/              # FRs, NFRs, traceability matrix
│   ├── project-management/        # Git strategy, risk register, charter
│   ├── adr/                       # Architecture Decision Records (ADR-001…)
│   ├── api/                       # Generated module/API docs
│   └── user-guide/
├── evidence/                      # Academic evidence, organised by unit (see §4)
│   ├── unit03/ … unit08/
│   └── EVIDENCE_REGISTER.md       # ID (E01–E20, roadmap §5) · description · file · date · used-in
├── reports/                       # Generated run output (git-ignored except samples/)
│   └── samples/                   # Curated sample reports committed for the portfolio
└── scripts/                       # Dev helpers (bootstrap, evidence capture, DB init)
```

### Layout rationale

| Decision | Rationale |
|---|---|
| `src/` layout | Prevents accidental imports of un-installed code; standard for pytest-based projects |
| One package per architecture component | Maps 1:1 to approved architecture and to Report §3.3 (components); each can be unit-tested and described independently |
| `core/` shared kernel | Single place for LLM access, masking/validation, metrics hooks, storage and models; components depend on `core`, never on each other's internals (see 04_COMPONENT_ARCHITECTURE.md §4) |
| `core/llm` includes a **mock provider** | Mitigates R1 (OpenAI failure), keeps CI deterministic and free of API cost |
| `prompts/` separate from code | Prompts are a primary quality lever; versioning them separately makes changes reviewable and evaluable |
| `tests/unit` mirrors `src` | Enforces "every module has unit tests" |
| `evidence/` in repo | Satisfies "produce screenshots/evidence for academic submission"; each item indexed to unit and report section |
| `sample-apps/` | Gives a controlled SUT where locator breakage can be injected reproducibly for self-healing evaluation; avoids testing client systems |

## 3. Module Template (applies to each component package)

```text
<component>/
├── __init__.py        # Public API only (what other components may import)
├── README.md          # Purpose, inputs, outputs, method, limits
├── service.py         # Orchestrating entry point of the component
├── interfaces.py      # Abstract contracts (ports) the component exposes/consumes
├── models.py          # Component-local data types
├── <impl modules>.py  # Implementation detail (private by convention)
└── (tests live in tests/unit/<component>/)
```

## 4. Evidence Folder Convention

```text
evidence/unitNN/
├── screenshots/   NN_<what>_<YYYYMMDD>.png
├── logs/          NN_<what>_<YYYYMMDD>.txt
├── test-results/  junit + coverage exports
(no per-unit index: every file is registered once in evidence/EVIDENCE_REGISTER.md using IDs E01–E20)
```

Screenshots are captured by the framework itself (FR-18) and by `scripts/capture_evidence.*` for CI runs, so submission evidence is reproducible rather than manually assembled. Capture rule (roadmap §5): timestamp visible, 2× scale, taken at run time.

**Evidence ID scheme:** the roadmap's **E01–E20** is used. `MASTER_PLAN.md` §9.4 lists an earlier **S01–S14** list for the same purpose; the two overlap and should be merged (see `project-management/SOURCE_ALIGNMENT_REVIEW.md`).

## 5. Mapping: Academic Workspace → Repository

| Workspace folder | Repo destination | Note |
|---|---|---|
| `architecture/` | `docs/architecture/` | Copy at each release tag |
| `project-management/` | `docs/project-management/` | Includes Git strategy |
| `SYSTEM_REQUIREMENTS/` | `docs/requirements/` | Superseded by files 02/03 once approved (see Open Items) |
| `cicd/` | `docs/architecture/` + `.github/workflows/` | Strategy doc → real workflows in Unit 4 |
| `security/` | `docs/security/` | OWASP/GDPR analyses |
| `evidence/` | `evidence/` | Register plus curated items |
| `final-report/`, `presentation/`, `knowledge/`, `rubrics/`, `01_UNIT_INSTRUCTIONS/`, `templates/`, `skills/` | **Not published** | Course-internal; keep in the private workspace. The Unit 8 portfolio publishes a curated subset via GitHub Pages |
| `source-code/` | Replaced by the repo itself | Currently a one-line placeholder |

## 6. Security and Hygiene Rules for the Repo

- No secrets, client names, client data or internal employer metrics committed (organisational confidentiality rule; roadmap issue I-12). Test only against public/demo applications.
- `.env` and `*.db` git-ignored; secret scanning in pre-commit and in `security.yml`.
- Dependencies pinned; Dependabot enabled. Python 3.12 is the reference runtime (approved stack, `MASTER_PLAN.md` §2).
- `CODEOWNERS` and branch protection enforce review gates (see `project-management/GIT_STRATEGY.md`).

## 7. Open Items

1. Final repository name and visibility (public for portfolio vs. private with instructor access).
2. Whether to keep `SYSTEM_REQUIREMENTS/` or consolidate into `architecture/` (this document set assumes consolidation).
