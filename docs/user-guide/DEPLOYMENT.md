# Deployment and Configuration Guide

Requirements: NFR-05 (repeatable runs), NFR-09 (key from the environment only), NFR-19 (containerised deployment), NFR-20 (documentation), NFR-26 (Windows and Linux, Python 3.12), NFR-27 (install in 15 minutes or less).

## 1. Deployment methods and the choice

| Method | Good for | Cost |
|---|---|---|
| Local virtual environment | Development, debugging, the VS Code workflow | Python 3.12, Chromium and Git on each machine |
| Docker image | Repeatable runs, demonstrations, CI | Docker on the host; Chromium is inside the image |
| GitHub Actions (`ci.yml`, `integration.yml`) | Automatic checks on every push and pull request | None beyond the repository |

**Choice.** Develop in the local virtual environment, ship and demonstrate with the Docker image, and let GitHub Actions build the image and run the whole pipeline inside it on every pull request. The image build is the only deployment test that does not depend on the author's machine. There is no registry push and no cloud hosting: the framework is a command-line tool, not a service (see section 8).

## 2. Prerequisites

| Item | Version | Check |
|---|---|---|
| Python (local method) | 3.12 | `python --version` |
| Git | recent | `git --version` |
| Docker (container method) | 24 or newer | `docker --version` |
| Network access | for installing packages and, only with `LLM_PROVIDER=openai`, `api.openai.com` | |
| OpenAI API key | only for live runs | never needed for tests, CI or the mock provider |

## 3. Configuration

All settings are read from the process environment; a JSON file given with `--config` may set the same names in lower case (never the key). The environment wins over the file.

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` (no network, no cost) or `openai` |
| `OPENAI_API_KEY` | none | required only when the provider is `openai`; kept in memory, never logged, never in generated files |
| `LLM_MODEL` | `gpt-4o-mini` | model name for the live provider |
| `LLM_CALL_CAP` | `100` | maximum model calls per run (budget guard, ADR-026) |
| `LLM_MAX_RETRIES` | `3` | retries with exponential back-off (0 to 10) |
| `LLM_TIMEOUT_S` | `30` | seconds before a call is abandoned |
| `LLM_CACHE_DIR` | `.aitaf_cache/llm` | replay cache for identical prompts; empty turns it off |
| `LLM_PRICE_IN_PER_1K`, `LLM_PRICE_OUT_PER_1K` | `0` | USD per 1,000 tokens, for the cost column |
| `LOG_LEVEL` | `INFO` | log level |

An invalid value stops the program with a clear message and exit code 2 before anything runs.

**Configuration management.** Defaults live in code; a `.env` file (git-ignored) or the shell supplies overrides; the key lives only in the shell or a secret store. The repository holds a template with no values for secrets: copy it to `.env` and edit.

```text
# .env.example (copy to .env; never commit .env)
LLM_PROVIDER=mock
OPENAI_API_KEY=
LLM_MODEL=gpt-4o-mini
LLM_CALL_CAP=100
LLM_MAX_RETRIES=3
LLM_TIMEOUT_S=30
LLM_CACHE_DIR=.aitaf_cache/llm
LLM_PRICE_IN_PER_1K=0
LLM_PRICE_OUT_PER_1K=0
LOG_LEVEL=INFO
```

## 4. Local installation (Windows or Linux)

```text
git clone https://github.com/Deelip17/UoP_Capston_Project_dilip.git
cd UoP_Capston_Project_dilip
python -m venv .venv
.venv\Scripts\activate            # Linux and macOS: source .venv/bin/activate
python -m pip install -r requirements-dev.txt -r requirements-report.txt
python -m playwright install chromium
python -m pip install -e . --no-deps
```

Verify:

```text
aitaf --help
python -m pytest -q
```

## 5. Docker image

Build (about 2 to 4 minutes; the image holds Python, the framework and Chromium):

```text
docker build -t aitaf:local .
```

Run the whole pipeline against the built-in demonstration shop with the mock provider; outputs go to the mounted `reports` folder:

```text
docker run --rm --ipc=host -v "$(pwd)/reports:/app/reports" aitaf:local run \
  --input data/requirements/shop_requirements.md --db reports/aitaf.db \
  --out-dir reports/pipeline --demo-shop --approve-all
```

With a live model (the key is passed from the host environment, not written into the image):

```text
docker run --rm --ipc=host -e LLM_PROVIDER=openai -e OPENAI_API_KEY -v "$(pwd)/reports:/app/reports" aitaf:local run ...
```

Use `--approve-all` only for demonstrations: it approves every generated test case itself. Without it the run stops at the human review gate.

## 6. Build and verification in CI

`integration.yml` (pushes to `develop`, pull requests to `develop` and `main`, or on request) builds the image, checks `aitaf --help` inside it and runs the pipeline on the demonstration shop inside the container with the mock provider. No secret and no registry push is involved (ADR-025, ADR-026).

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `LLM_PROVIDER=openai requires OPENAI_API_KEY` | export the key in the shell that starts Docker or the CLI |
| Browser missing locally | `python -m playwright install chromium` |
| Chromium crashes in Docker | add `--ipc=host` (shared memory) |
| `unable to open database file` | give `--db` a path inside a folder that exists and is writable (`reports/aitaf.db`) |
| Output lost after `docker run` | mount a volume on `/app/reports` |

## 8. Not covered

No registry push, Kubernetes, cloud hosting or scheduled runs. The image runs as a non-root user but is not security-hardened beyond that; the shop server binds only to the loopback address. Selenium is supported by the generated scripts, but the image installs Chromium for Playwright only.
