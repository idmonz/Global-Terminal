# Phase 6F Implementation Report

Updated: 2026-07-03

## Delivered Journey

```text
Watchlist Desk
-> bounded five-symbol Research Snapshot
-> saved Price / Performance / Risk / Financials / Technicals / Catalysts
-> exact TSLA Catalyst workstation
-> source and freshness inspection
-> return to the same selection, mode, sort, group, and panel
```

## Implementation

- `lib/research_snapshot.py` adds the bounded provider-budget and LKG contract.
- `lib/watchlist_desk.py` reuses the existing materialization job and persists
  public research rows without creating another queue or scheduler.
- `lib/equity_provider_breadth.py` reuses Alpha Vantage overview for dividend
  fields, avoiding additional provider calls.
- `lib/symbol_intelligence.py` adds an exact-symbol `catalysts` delivery panel
  backed only by same-symbol research cache.
- `lib/api_contracts.py` exposes per-item research source registers.
- The Watchlist adds a Catalysts mode, catalyst monitor, provider-call ledger,
  failure/LKG messaging, and URL-stable state.
- The progressive workstation adds a Catalyst tab and a state-preserving return
  to Watchlist.
- The Phase 6F browser harness verifies desktop/mobile, exact return, rate-limit,
  offline/LKG, accessible names, duplicate IDs, focus visibility, and overflow.

## Live Evidence

The safe live smoke completed AAPL, TSLA, JNJ, TTE, and TMUS:

- cold observed run: 5/5 enriched, 12 actual calls, 4 cache hits, no failures,
  15.25 seconds;
- warm observed run: one history call, 15 cache hits, no failures, 1.365 seconds;
- observed next earnings dates were selected as nearest future events;
- displayed prices were independently cross-checked during QA.

Counts and dates are observations, not hard-coded product claims.

## Honest Boundaries

This slice does not add broker execution, recommendations, target prices,
hosted accounts, auth, billing, licensed real-time feeds, or an installed
background service. Fixture catalysts are explicitly fictional QA evidence.
Provider-backed rows retain live/cache/stale/rate-limit/unavailable truth.
