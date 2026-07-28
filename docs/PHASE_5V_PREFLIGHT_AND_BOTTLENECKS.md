# Phase 5V Preflight And Symbol Workstation Bottlenecks

Updated: 2026-06-30

## Current Truth

Phase 5V targets the visible symbol route, not another hidden contract layer. The durable master goal remains active.

Streamlit remains the internal lab/reference. `lib/` remains the reusable data, provider, quant and contract layer. `backend/api` is optional. `apps/web` is the commercial B2C product surface.

## Baseline Gates Before Product Edits

Commands run before product code edits:

| Command | Result | Notes |
|---|---|---|
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --collect-only -q` | passed | Collected repository tests by module. |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -x` | passed | Existing FastAPI deprecation and cointegration collinearity warnings only. |
| `python -m compileall -q app.py lib pages scripts tests backend` | passed | No compile errors. |
| `python scripts/export_api_fixtures.py` | passed | 27 deterministic API fixtures exported. |
| `npm.cmd --prefix apps/web test` | passed | Fixture/runtime UI validation passed. |
| `npm.cmd --prefix apps/web run lint` | passed | No lint output. |

## Reference Screens Inspected

Clean-room visual references were inspected from `external (2)`:

| Reference | Behavior evidence used |
|---|---|
| `tradingview.PNG` | Symbol financials/earnings/revenue depth plus right watchlist and selected-symbol side context. |
| `openbb.png` | Source-aware widget grid: ticker information, profile, chart, news and copilot context on one workspace. |
| `finviz.PNG` | Market-map discovery to symbol drilldown, heatmap density and quick ticker navigation. |
| `worldmonoitor.PNG` | Map/news/financial-impact/AI panels visible together, not hidden in diagnostics. |
| `터미널 예시.png` | Dense Korean terminal layout with chart, score strips, events, news, filings and compact side modules. |

No external source code, visual asset, font, dataset or trade dress was copied.

## Before-State Visual Evidence

Baseline screenshots and metrics:

`review_workspace/phase5v_before/baseline-report.json`

| Route | Status | Chart top | Chart width | Compare overlap | Exact news | Source ledger | Context cards | Main visible defect |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| AAPL desktop | fixture | 696px | 1096px | 0 | 0 | 0 | 3 | Runtime fallback diagnostics and controls push the actual workstation down; comparison/news vanish without runtime API. |
| MSFT desktop | fixture | 678px | 1054px | 0 | 0 | 0 | 3 | Same fallback/catalog issue; no source ledger in first viewport. |
| SPY desktop | fixture | 678px | 1054px | 0 | 0 | 0 | 3 | ETF context exists but does not feel like a benchmark-grade symbol desk. |
| BTCUSDT desktop | fixture | 696px | 1096px | 0 | 0 | 0 | 3 | Crypto derivatives label exists, but compare/news/source matrix are not operationally visible. |
| ETHUSDT mobile | fixture | 976px | 351px | 0 | 0 | 0 | 3 | Mobile chart starts far below the first screen. |
| Unknown symbol | unknown-symbol | 0px | 0px | 0 | 0 | 0 | 0 | Correctly avoids fixture substitution. |

The previous `npm.cmd --prefix apps/web run visual:phase5n` harness currently fails on:

`aapl-live-candlestick-desktop: comparison overlap missing`

Direct Python contract check showed the backend contract can compute AAPL/SPY overlap, but the Next.js route falls back to static catalog data when the optional runtime API is unavailable. The catalog selection path does not recompute route-local comparison, so the visible web route loses a feature that exists in `lib/`.

## Phase 5V Fix Plan

1. Keep the chart dominant but move real working content higher by compressing diagnostics and controls.
2. Add a compact first-viewport intelligence deck: source state, history rows, compare overlap, exact-news count, financial/options or crypto-derivatives boundary.
3. Add an inspectable first-viewport source ledger/matrix without letting diagnostics dominate the page.
4. Add `Options` as a real equity surface and a `Derivatives` equivalent in crypto overview context.
5. Recompute static-catalog comparison in the web fallback path when the requested compare symbol exists in the catalog, explicitly labeled as fixture/static and not live.
6. Improve overview cards so news/events, map/market links, peer comparison and provider gaps are visible together.
7. Build a Phase 5V visual harness for AAPL/MSFT/SPY/BTCUSDT/ETHUSDT/unknown on desktop/mobile.

## Acceptance Criteria

- AAPL/MSFT/SPY/BTCUSDT/ETHUSDT routes show a nonblank chart and visible intelligence modules in the first working viewport.
- Static fallback does not silently drop comparison when a same-catalog compare symbol is available.
- Unknown symbols still do not substitute another symbol.
- Equity surfaces expose an options bridge without OPRA/live execution claims.
- Crypto surfaces expose funding/basis/open-interest boundaries without liquidation/account claims.
- Every new visible claim remains provider/source/freshness/caveat/data-gap aware.
- Desktop/mobile screenshots are captured and inspected.
