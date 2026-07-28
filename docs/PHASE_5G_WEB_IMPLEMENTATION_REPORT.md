# Phase 5G Web Implementation Report

Updated: 2026-06-19

## Delivered Journey

`Market Home -> AAPL -> Home -> BTCUSDT -> unknown symbol` is now a coherent web workflow with refresh-stable query state.

## Product Changes

- Added `apps/web/src/lib/product-routes.ts` for canonical asset URLs, allowlisted timeframes, surface selection, normalization, and unsupported-symbol classification.
- Reworked the root Next.js page into a product-first Market Home with cross-asset tape, heatmap, real chart renderer, news feed, symbol search, and compact source truth.
- Added product navigation for Home, AAPL, BTCUSDT, War Map, News, Screener, and Providers. The 20 fixture/API surfaces remain under diagnostics rather than primary navigation.
- Added AAPL overview, financials, and options-readiness tabs without claiming a live option chain or dealer positioning.
- Added BTCUSDT price, open-interest, funding, taker-flow, scenario, and pressure-proxy work surfaces from the existing crypto contract.
- Added explicit unknown-symbol UI and source boundary; no AAPL/BTC fixture rows leak into that state.
- Added runtime request symbol propagation and visible cache/runtime fallback.
- Added chart `ready`, `fallback`, and point-count DOM markers plus a controlled `chartMode=fallback` diagnostic path.
- Updated screener drilldown URLs to the canonical asset route.

## Data Verdict

- Fixture mode: deterministic, source-labeled, non-advisory, renderable.
- Cache/live mode: existing optional FastAPI and provider paths are reused when configured.
- API not configured: explicit `runtime-fallback`; static rows never appear live.
- Unknown symbol: explicit unavailable; no synthetic substitute.
- Options chain/GEX/dealer flow: provider-required/unavailable.

## Remaining Product Gaps

- Most symbols beyond AAPL/BTCUSDT do not yet have product coverage.
- Timeframe controls preserve URL state but do not yet change provider interval/range.
- Default local product still needs FastAPI configuration for runtime rows.
- Heatmap constituents are deterministic clean-room fixtures.
- Global map, screener universe, portfolio, and research memory remain below commercial parity.
