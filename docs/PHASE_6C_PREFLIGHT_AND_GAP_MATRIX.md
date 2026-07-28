# Phase 6C Preflight And Gap Matrix

Updated: 2026-07-02

## Objective

Turn the Phase 6B Market Map into an exact discovery-to-analysis journey. A
materialized supported identity must open its own bounded, provider-backed Symbol
Workstation with symbol-isolated cache/LKG behavior, useful chart and analysis
context, honest source gaps, and a preserved return to the originating Market Map
state.

## Toolchain And Configuration

- Python 3.14.5;
- yfinance 0.2.66;
- Node 24.16.0;
- npm 11.13.0;
- local FastAPI `127.0.0.1:8004`;
- production Next.js `127.0.0.1:3045`;
- `SEC_USER_AGENT`, `ALPHAVANTAGE_API_KEY`, `FINNHUB_API_KEY`, and
  `GEMINI_API_KEY`: present by key-presence check only.

No credential value was read or printed.

## Baseline Gates

- full Python: 876 passed with the existing TestClient and cointegration
  warnings;
- compileall and smoke imports: passed;
- deterministic fixture export: 27 fixtures;
- web fixture/runtime test, ESLint, and Next.js production build: passed;
- npm audit: zero vulnerabilities;
- source release: 1,535 entries.

## External Reference Audit

The deterministic external audit was rerun under
`review_workspace/external2_analysis/phase6c`:

- 28 archives and 51,305 file entries;
- 38,623 indexed non-vendored text/code files;
- 8,742,912 indexed lines;
- 556 vendored files and 38 oversized files explicitly skipped;
- zero archive hash changes from Phase 6B;
- 18 direct-use, 6 behavior-only, 3 needs-review, and 1 blocked license classes.

Mechanical indexing is not individual semantic human review. OpenBB, OpenStock,
WorldMonitor, worldview, and unclear-license projects remain behavior-only where
their license boundary requires it. No external source or asset is copied in this
phase.

## Measured Product Gap

- materialized Market Map identities: 333;
- static Symbol Directory identities: 90;
- materialized identities currently resolved by the Symbol Workstation: 60;
- materialized identities currently ending as unknown/dead-end: 273;
- exact workstation activation coverage: 18.02%;
- current stored Market Map payload: 866,907 JSON bytes;
- current snapshot status during preflight: stale/LKG.

The gap is not chart rendering. It is identity activation: the web route and
Python resolver still trust the old bounded static registry rather than the
current materialized Nasdaq/SEC-reconciled identity store.

## Visual Baseline

`apps/web/scripts/capture-phase6b.mjs` was rerun against the production build:

- 333 rows and 333 tiles;
- 333 classified rows, 273 provider-classified, 60 reviewed industries;
- one visible taxonomy conflict and 11 canonical sectors;
- desktop first useful paint: 1,287 ms;
- mobile first useful paint: 1,081 ms;
- hierarchy interaction: 79 ms;
- no page overflow or browser errors;
- unknown `NOTAREAL123` remained unknown with no Apple identity leakage.

Evidence is stored under
`review_workspace/phase6b_visual_phase6c-preflight`.

## Proof Symbols

Phase 6C must visually prove at least four non-AAPL identities. The primary set is:

- `TSLA`: Nasdaq / Consumer Discretionary;
- `JNJ`: NYSE / Health Care;
- `TTE`: NYSE / Energy;
- `TMUS`: Nasdaq / Communication Services.

All four are present in the materialized snapshot but unresolved by the old
static directory at preflight. `MSFT`, `JPM`, `XOM`, and `WMT` remain useful
regression controls.

## Budgets And Abuse Cases

- activate all valid supported identities in the current 333-row snapshot;
- exact lookup only; malformed, traversal, unsupported, and unknown input stays
  unavailable;
- no cross-symbol fixture, cache, SEC, news, or financial leakage;
- cache key includes symbol, asset class, interval, range, and panel contract;
- selected-symbol calls never rebuild the broad Market Map;
- provider calls are bounded to the selected symbol and optional comparison;
- warm exact-symbol API p50 below 750 ms;
- provider failure uses same-symbol stale/LKG or explicit unavailable state;
- desktop/mobile remain chart-first with no page overflow or layout shift;
- no secrets, private paths, external archives, cache files, advice, targets,
  broker actions, or autonomous language cross the API/release boundary.

