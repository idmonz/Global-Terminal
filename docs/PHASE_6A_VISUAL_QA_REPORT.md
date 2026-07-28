# Phase 6A Visual QA Report

Updated: 2026-07-01

## Harness

`npm --prefix apps/web run visual:phase6a`

The harness was run against:

- online API: web 3045 / API 8004;
- forced stale API: web 3046 / API 8005 with zero freshness allowance;
- controlled invalid API: web 3047 / API 8999.

## Evidence

Online:

- Market Map desktop/mobile: 137 rows and 137 tiles;
- snapshot: fresh, refresh succeeded, 2 observed provider calls;
- AAPL Financials: 44 SEC facts, 8 earnings rows;
- SEC unit/form context visible;
- Market Map -> AAPL -> return preserved query, selected symbol, size, and color;
- unknown symbol explicit, no Apple identity leakage.

Stale:

- 137 last-known-good rows remained visible;
- snapshot state displayed as amber `stale`;
- refresh duration and provider-call count remained visible.

Offline:

- 30 deterministic fixture rows remained visible;
- runtime was explicitly unreachable;
- SEC facts and earnings were explicitly unavailable;
- no fabricated live state.

All desktop/mobile captures had meaningful bytes, no page-level horizontal
overflow, and zero console/page errors.

## Personally Inspected

- `review_workspace/phase6a_visual_online/market-map-desktop.png`
- `review_workspace/phase6a_visual_online/aapl-financials.png`
- `review_workspace/phase6a_visual_online/market-map-mobile.png`
- `review_workspace/phase6a_visual_stale/market-map-desktop.png`
- `review_workspace/phase6a_visual_offline/aapl-financials.png`

The dense terminal layout is coherent. Mobile is intentionally long but does not
overflow. The SEC/earnings evidence grid is readable and stale truth is visually
distinct.

