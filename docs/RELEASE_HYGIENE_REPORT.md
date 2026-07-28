# Release Hygiene Report

## Scope

This pass fixed generated-artifact hygiene and clarified the WorldMonitor runtime boundary.

## Pre-Flight Gate

- `python scripts/run_smoke_tests.py`: passed before edits.
- `python -m pytest -q`: passed before edits, 72 tests.
- Canonical functions in `market_data.py`, `global_markets.py`, `heatmaps.py`, and `crypto_derivatives.py`: present.
- Static universes:
  - `static/index_constituents/sp500.csv`: 60 rows.
  - `static/index_constituents/nasdaq100.csv`: 30 rows.
  - `static/index_constituents/korea_watchlist.csv`: 24 rows.

## Ignore Rules

`.gitignore` now includes generated artifacts, private data, external references, and local secrets:

- `__pycache__/`
- `**/__pycache__/`
- `.pytest_cache/`
- `*.pyc`
- `*.pyo`
- `*.log`
- `data/cache/`
- `external/`
- `_recovery/`
- `.env`
- `.venv/`
- `venv/`
- `.DS_Store`
- `data/portfolio.json`
- `data/raw/`
- `data/private/`
- `.streamlit/secrets.toml`

## Cleanup

Cleanup used only the approved script:

- `python scripts/safe_cleanup_generated_artifacts.py --dry-run`
- `python scripts/safe_cleanup_generated_artifacts.py --execute`

The execute pass removed:

- `tests/__pycache__`
- `lib/__pycache__`
- `data/cache`
- `.pytest_cache`

After final validation, a second cleanup pass removed:

- `tests/__pycache__`
- `pages/__pycache__`
- `lib/__pycache__`
- `data/cache`
- `__pycache__`
- `.pytest_cache`

## WorldMonitor Boundary

- `external/worldmonitor-main/` is reference-only.
- Runtime Python files do not import from `external/`.
- Runtime modules do not copy WorldMonitor TypeScript or AGPL source.
- Optional adapter calls stay inside `lib/worldmonitor_adapter.py`.
- Private or pro-gated surfaces are not scraped.
- Live AIS or vessel flow is unavailable unless a real provider is configured.

## Final Hygiene Note

Test runs can recreate Python and pytest caches. The final validation sequence ran tests first, then the cleanup script was run again so generated cache artifacts could be removed after validation. A final filesystem check found no `__pycache__/`, `.pytest_cache/`, `*.pyc`, `*.pyo`, `*.log`, or `data/cache/*.json` artifacts.
