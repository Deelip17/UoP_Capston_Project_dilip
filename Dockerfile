# AITAF container image (NFR-05, NFR-26, NFR-27). Build: docker build -t aitaf:local .
# Contains the framework, Chromium and the report extras. No API key or other secret is
# baked in: pass settings at run time (docker run --env-file .env ...), see .env.example.

FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Playwright's bundled Node needs libatomic before it can install the browser's own packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first so the layer is reused when only the source changes
COPY requirements.txt requirements-report.txt ./
RUN python -m pip install -r requirements.txt -r requirements-report.txt \
    && python -m playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright

# The package and the data the demonstration needs (sample requirements, page snapshots)
COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
RUN python -m pip install --no-deps .

# Run as an ordinary user; outputs go to /app/reports (mount a volume there to keep them)
RUN useradd --create-home --uid 10001 aitaf \
    && mkdir -p /app/reports \
    && chown -R aitaf:aitaf /app
USER aitaf
VOLUME ["/app/reports"]

ENV LLM_PROVIDER=mock
ENTRYPOINT ["aitaf"]
CMD ["--help"]
