# WorldMonitor Audit

WorldMonitor is treated as an architectural reference and optional adapter target, not as a runtime dependency.

## Boundary

- Do not vendor TypeScript/Tauri code into this Streamlit app.
- Do not scrape private or pro-gated surfaces.
- Optional API calls are isolated in `lib/worldmonitor_adapter.py`.
- Missing key, 401, 403, 404, timeout, and invalid JSON paths return normalized `DataResult` objects.

## Conceptual Reuse

- Route intelligence concepts
- Chokepoint registry patterns
- Energy/geopolitical intelligence panel structure
- Scenario-style risk summaries

## MVP Scope

Python equivalents are implemented from public/free sources and local registries. WorldMonitor remains optional.

