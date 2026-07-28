# Phase 6H Implementation Report

Updated: 2026-07-03

## Outcome

Phase 6H composes the exact symbol, progressive panel, saved-change, source,
map, and command boundaries into one synchronized analyst workspace.

Implemented:

- `lib/analyst_workspace.py`
  - compact `analyst_workspace.v1` manifest;
  - exact identity, panel compatibility, request plan, source clocks, safe
    return state, local layout boundary, and change-to-panel mapping.
- `lib/api_contracts.py` and `backend/api/app.py`
  - `analyst_workspace` envelope;
  - ETag-enabled `GET /api/analyst-workspace/{symbol}`;
  - exact saved-change lookup with no cross-symbol substitution.
- `apps/web/src/components/AnalystWorkspace.tsx`
  - simultaneous chart, financial, catalyst, and source panes on desktop;
  - compact selected-panel mobile flow;
  - symbol, interval, range, comparison, panel, and layout synchronization;
  - in-flight request deduplication, ETag reuse, and same-symbol LKG retention;
  - local-only layout presets, bounded split control, save/reset, focus
    shortcuts, verified map/command actions, and stateful Change Inbox return.
- `scripts/export_api_fixtures.py`
  - exact compact workspace catalog and exact saved primary-chart catalog;
  - duplicated `chart_specs` removed from initial saved primary delivery.
- `apps/web/scripts/capture-phase6h.mjs`
  - production desktop/mobile/live/failure/slow/synchronization/journey gates.
- `scripts/benchmark_phase6h.py`
  - reproducible manifest and panel latency/payload measurements.

## Product Journey

```text
Change Inbox
-> select exact saved event
-> open AAPL analyst workspace focused on Catalysts
-> inspect before/after change plus chart, financials, catalysts, and sources
-> open evidence or verified map/command routes
-> return to the same list, filters, symbol, and change
```

The fixture journey is deterministic and fictional. Live mode independently
revalidates the saved primary panel and updates quote and market/source clocks.

## Data And Action Boundary

- No broker, order, target, sizing, autonomous AI, hosted-layout, or alert
  delivery action was added.
- Desktop composition makes at most four exact panel requests.
- Mobile sends no hidden-panel request before user action.
- Timeframe changes invalidate chart-compatible panels only.
- A failed refresh retains only a matching symbol/panel/timeframe LKG body and
  labels the failed attempt.
- Layout storage excludes notes, credentials, provider bodies, local paths, and
  arbitrary URLs.

## Live Observation

On 2026-07-03, AAPL live-if-available rendered:

- 62 yfinance OHLCV rows;
- 308.63 USD last price;
- yfinance plus SEC-backed financial context;
- stale catalyst evidence labeled stale rather than fresh;
- five source/provenance rows.

An independent market lookup also returned 308.63 USD. This is a
time-dependent observation, not a hard-coded test value or real-time guarantee.

## Clean-Room Result

All 28 supplied archives were re-audited. OpenBB, TradingView, Bloomberg-like,
BB-Terminal, WorldMonitor, and worldview references informed behavior and
workflow only. No external code, dataset, font, image, or trade dress was
copied.

