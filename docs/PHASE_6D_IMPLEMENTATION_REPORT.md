# Phase 6D Implementation Report

Updated: 2026-07-02

## Delivered Journey

```text
Market Home / navigation
-> Watchlist Desk
-> create or select a local-private list
-> add exact identities
-> bounded five-symbol materialization
-> switch symbols in place
-> chart first
-> financial, news, and source panels on demand
-> open the full workstation with origin state
```

## Core Changes

- `lib/watchlist_desk.py` implements named-list CRUD, exact identity validation,
  public row shaping, privacy exclusion, bounded materialization, and job health.
- workspace schema v8 and migration add list/order/job persistence.
- `lib/symbol_intelligence.py` adds summary/chart/financials/news/sources
  delivery contracts without changing the compatible full contract.
- `lib/api_contracts.py` and `backend/api/app.py` expose desk and panel routes.
- `static/api-fixtures/watchlist-desk.json` provides a deterministic five-symbol
  offline boundary.
- `WatchlistDesk.tsx` provides the dense daily-use UI and lucide controls.
- the Watchlist route now returns before loading all 28 fixtures.
- `FinanceChart.tsx` constrains desktop height hints to responsive container
  limits, preventing mobile canvas overflow.

## Observed Runtime

A dedicated private QA database materialized AAPL, TSLA, JNJ, TTE, and TMUS:

- 5 requested, 5 completed, 0 failed;
- 62 daily OHLCV rows per symbol;
- one provider call within a budget of five;
- 458 ms observed job duration;
- broad universe rebuild: false.

At the observation time, the US regular session was not open. The UI therefore
kept session freshness conservative while the five displayed prices exactly
matched independent current quote lookup values.

## Performance

Warm local samples:

| Surface | Bytes | p50 | p95 |
|---|---:|---:|---:|
| Watchlist API | 9,775 | 120 ms | 296 ms |
| TSLA summary API | 19,622 | 24 ms | 30 ms |
| TSLA chart panel | 163,264 | 246 ms | 264 ms |
| TSLA financial panel | 62,496 | 64 ms | 75 ms |
| TSLA news panel | 27,800 | 30 ms | 33 ms |
| TSLA full API | 215,008 | 253 ms | 260 ms |

The final production Watchlist document is 47,676 bytes versus 1,071,952 bytes
for the direct full TSLA workstation, a 95.6% reduction. The
direct full workstation remains deliberately available and is a Phase 6E target.

## Explicit Non-Claims

No broker execution, recommendation, target, position sizing, hosted account,
billing, background daemon, alert delivery, paid provider requirement, or
real-time exchange entitlement was added.
