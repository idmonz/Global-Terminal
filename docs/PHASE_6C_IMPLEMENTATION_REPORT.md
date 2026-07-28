# Phase 6C Implementation Report

Updated: 2026-07-02

## Outcome

Phase 6C converts the 333-row Market Map from a broad discovery surface with 273
dead ends into an exact discovery-to-analysis journey. All 333 current supported
materialized identities can now open their own Symbol Workstation.

## Runtime And Contract Changes

- `lib/symbol_workstation.py`
  - adds materialized identity conversion/reconciliation;
  - adds runtime directory composition and capability planning;
  - enforces symbol-scoped cache/LKG and explicit unavailable behavior;
  - upgrades the contract to `symbol_workstation.v2`.
- `lib/symbol_intelligence.py`
  - consumes materialized CIK and market context;
  - bounds supplemental providers by mode and panel;
  - exposes exact financial, SEC, news, comparison, and source context;
  - upgrades to `symbol_intelligence.v2`.
- `lib/market_snapshot_store.py`
  - retains compact trend and valuation availability/detail fields;
  - final refreshed snapshot contains 333 supported rows in 888,701 source JSON
    bytes with 15 bounded provider calls.
- `lib/market_map_screener.py`
  - treats current official supported identities as workstation-capable.
- `backend/api/app.py`
  - adds exact-symbol routing, stable ETag/304, private cache control, and
    isolated 404 behavior.
- `lib/api_contracts.py` and `scripts/export_api_fixtures.py`
  - expose the runtime directory while preserving deterministic static fixtures.

## Web Product Changes

- runtime symbol search and asset routes accept safe dynamic equities;
- the API remains the final authority for supported identity;
- Market Map rows no longer dead-end because they are outside the old static set;
- Symbol Workstation shows an exact identity evidence strip with exchange/MIC,
  CIK, sector/classification origin, conflict truth, and fetch budget;
- chart, technical, risk, comparison, financial, SEC, news, and source panels
  reuse the same exact payload;
- Market Map query, selected symbol, size, color, and sector survive the round
  trip;
- loading, cache, unavailable, unknown, and offline states remain distinct.

## Measured Result

- activation coverage: 60/333 (18.02%) to 333/333 (100%);
- runtime directory: 363 unique identities;
- final snapshot: 333 rows, 333 workstation-capable, 333 sector-classified,
  60 reviewed industries, one explicit conflict;
- final snapshot refresh: 14.1 seconds, 15 bounded provider calls;
- warm direct TSLA builder: p50 120 ms, p95 261 ms;
- warm HTTP TSLA: p50 181 ms, p95 250 ms;
- warm HTTP TTE: p50 144 ms, p95 158 ms;
- exact API ETag conditional read: 304;
- unknown exact symbol: 404 with no Apple/AAPL leakage.

Cold selected-symbol provider composition remains slow at roughly 12.8-14.8
seconds in observed first calls. Reducing that latency and the approximately
1.07 MB SSR page is the next product bottleneck.

## Boundaries

No broker execution, advice, target, position sizing, paid-provider dependency,
hosted auth/billing, external source copy, or fabricated live row was added.
Streamlit remains the internal lab; reusable logic stays in `lib/`, API routing
in `backend/api`, and commercial product UI in `apps/web`.

