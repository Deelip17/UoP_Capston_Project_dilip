# Dashboard

A static HTML page that shows how the framework performs across all stored runs.
Requirements: FR-33 (pass rate, healing, accuracy, coverage, executability, cost, latency,
trend over at least three runs), NFR-29 (readable by non-technical readers).

## Use

```
aitaf dashboard --db aitaf.db --out reports/dashboard [--last N] [--labels labels.csv]
```

Writes `dashboard.html`, `dashboard.csv` (the raw table) and `charts/*.png`.
Charts need matplotlib: `pip install -r requirements-report.txt`.

## How it works

- `data.py`: one Pandas row per run with results, built from `aitaf.reporting.build_report`,
  so every figure equals the run report's. A metric that cannot be computed is missing
  (shown "n/a"), never zero.
- `charts.py`: three PNGs in one hue on a light surface.
- `render.py`: offline page (no scripts, no external links): latest-run tiles first, then
  the trend charts, the run table and the basis of each number. Each chart has a text
  alternative; the provider (mock or live) is shown per run.

## Not built

- No live server, filters or interactive charts (static page only; polish is Should).
- Coverage, executability and cost use the latest analysis run as source for every run.
- Mock-provider figures describe the pipeline, not model quality.

It is a wiring package (like `evaluation`): it may import components; vendor rules still apply.
