# Goal 10B Pre-Flight Report

## Baseline Tests

- `python scripts/run_smoke_tests.py`: passed before Goal 10B implementation.
- `python -m pytest -q`: passed before Goal 10B implementation.

## Canonical Guard Status

- Market data exports exist: `empty_frame`, `fetch_history`, `fetch_multi_history`, `latest_close`.
- Global market universes exist: `SECTOR_ETFS`, `G7_MARKETS`, `CROSS_ASSET_TICKERS`, `CRYPTO_MARKETS`.
- Existing heatmap builders exist: S&P 500, Nasdaq 100, Korea, sector, G7, cross-asset, and crypto.
- Unified data layer exports exist: `request_data`, price history, financials, screener, macro, energy, and War Room payload routes.
- Command UX exports exist: `parse_terminal_command`, `route_terminal_command`, `build_terminal_function_registry`.
- Provider probe compatibility gap found and resolved before proceeding:
  - Added `build_probe_registry`
  - Added `run_provider_probe`
  - Added `run_all_lightweight_probes`
  - Added `build_provider_probe_summary`
- War Room and crypto canonical exports exist.

## Static Universe Counts

- `static/index_constituents/sp500.csv`: 60 rows, minimum 60.
- `static/index_constituents/nasdaq100.csv`: 30 rows, minimum 30.
- `static/index_constituents/korea_watchlist.csv`: 24 rows, minimum 24.

## Release Hygiene Status

- `.gitignore`, `.env.example`, `requirements-openbb.txt`, and `scripts/build_release_zip.py` exist.
- Fresh release zip hygiene check passed against `dist/global_market_terminal_20260611T113206Z.zip`.
- Required root files are included: `.gitignore`, `requirements.txt`, `requirements-openbb.txt`, `.env.example`, `app.py`.
- Forbidden paths were absent: `external/`, cache/private data, pycache, pytest cache, `.env`, `.env.*` other than `.env.example`, logs, compiled Python files, provider probe JSON, and Streamlit secrets.

## Visual System Baseline

- `lib/terminal_ui.py` already provides dark-mode cards, badges, metric strips, workspace presets, provider health strip, and summary strips.
- Baseline design is functional and compact, but it needs a clearer modern token layer, more explicit click paths, keyword chips, command help payloads, and confidence/freshness affordances reusable across pages.

## Heatmap Baseline

- `lib/heatmaps.py` builds static-universe-backed market heatmap data and enriches rows with yfinance where available.
- Existing heatmap rows include returns, realized volatility, drawdown, regime, and data quality labels.
- Baseline does not yet provide the requested tile engine, drilldown engine, tooltip system, modern color buckets, provider/source/portfolio/War Room/Energy heatmap payloads, or optional external widget disclaimers.

## War Room / Energy / News Baseline

- War Room is already map-first and shows event maps, right rail panels, layers, source status, hotspots, and missing live AIS caveats.
- Energy Geopolitics already exposes chokepoint maps, route proxies, EIA optional state, AIS optional state, energy fundamentals, news proxy, scenarios, and source status.
- News already includes feed clustering, impact visuals, catalyst graph, maps, source freshness, AI brief context, and clear WorldMonitor boundary notes.
- Goal 10B will consolidate these into reusable map layer, marker, tooltip, cluster, energy map, and news dashboard engines.

## Provider Probe Baseline

- `lib/provider_probe_runner.py` supports lightweight no-key/free-key provider probes, dry-run behavior, and nonfatal missing-key states.
- `scripts/run_provider_probes.py` exists.
- Split probe scripts requested by Goal 10B are not present yet and are part of implementation.

## Blockers

- No remaining baseline test blocker after adding provider probe compatibility wrappers.
- No release hygiene blocker found.
