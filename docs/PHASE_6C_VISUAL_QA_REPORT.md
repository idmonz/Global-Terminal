# Phase 6C Visual QA Report

Updated: 2026-07-02

## Harness

`apps/web/scripts/capture-phase6c.mjs` validates online, cache, provider-failure,
and API-offline scenarios. The in-app browser was unavailable after the required
bootstrap check, so the repository Playwright/Chrome harness was used.

## Online Proof

Final evidence:
`review_workspace/phase6c_visual_online-proof/summary.json`.

| Symbol | Sector | History | Chart points | Exact news | First useful paint |
|---|---|---:|---:|---:|---:|
| AAPL | Information Technology | 62 | 180 | 11 | 1,946 ms |
| TSLA | Consumer Discretionary | 62 | 180 | 12 | 1,640 ms |
| JNJ | Health Care | 62 | 180 | 12 | 1,697 ms |
| TTE | Energy | 62 | 180 | 12 | 1,673 ms |
| TMUS | Communication Services | 62 | 180 | 11 | 2,003 ms |

All five desktop routes showed a ready chart, 62 candles, 35 canvas elements,
materialized exact identity, source ledger, bounded provider budget, and
`broad_rebuild=false`.

TSLA mobile rendered a 351 px chart with no document overflow. TSLA Financials
showed 44 SEC facts. The dedicated inspected filing crop clearly displayed
reported fact, period, value/unit, form, and filed date.

## Cache, Failure, And Offline

- cache: TSLA desktop and JNJ mobile retained exact ready charts and
  symbol-specific news without provider promotion;
- provider failure: unsupported TSLA `15m/1y` used zero provider budget, showed
  no fabricated history, retained only the separately labeled delayed quote, and
  rendered the fallback state;
- unknown: `NOTAREAL` stayed unknown and contained no Apple identity;
- offline: AAPL explicit fixture mode rendered 48 deterministic rows, while
  dynamic TSLA stayed honestly unknown when the API was intentionally invalid;
- every scenario had zero browser/page errors and no horizontal overflow.

## Origin Round Trip

The final Market Map return preserved:

- query `TSLA`;
- selected symbol `TSLA`;
- size `equal`;
- color `relative_volume`;
- sector `Consumer Discretionary`.

## Personally Inspected

- `review_workspace/phase6c_visual_online-proof/tsla-online-desktop.png`
- `review_workspace/phase6c_visual_online-proof/tsla-online-mobile.png`
- `review_workspace/phase6c_visual_online-proof/tsla-online-financials.png`
- `review_workspace/phase6c_visual_online-proof/tsla-online-financials-sec-facts.png`
- `review_workspace/phase6c_visual_online-proof/tsla-market-map-round-trip.png`
- `review_workspace/phase6c_visual_failure-final/tsla-unsupported-capability.png`
- `review_workspace/phase6c_visual_offline-final/aapl-offline-fixture.png`

The product is materially more useful than the Phase 6B dead-end flow. It is
still below TradingView/OpenBB daily-workspace depth because the mobile page is
long, watchlist switching is not yet a first-class desk, and cold provider
composition is visibly slow.
