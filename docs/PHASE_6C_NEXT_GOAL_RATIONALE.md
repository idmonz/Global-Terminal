# Phase 6C Next Goal Rationale

Updated: 2026-07-02

## Evidence

Phase 6C removes the 273-row discovery dead end:

- exact workstation activation is now 333/333;
- four previously unsupported non-AAPL identities pass visual proof;
- exact chart, financial, SEC, news, source, failure, and origin-return behavior
  is usable;
- warm exact APIs are comfortably below the 750 ms budget.

The next largest daily-use defect is no longer identity activation. It is repeat
delivery:

1. a cold selected-symbol provider composition takes roughly 12.8-14.8 seconds;
2. the server-rendered workstation response is approximately 1.07 MB because all
   panels travel together;
3. existing local watchlist engines are not yet a first-class web desk for fast
   symbol switching;
4. users cannot pre-materialize a bounded watchlist and see per-symbol refresh,
   stale, or failure health;
5. mobile is correct but very long.

## Selected Next Phase

Phase 6D: Watchlist Desk And Materialized Workstation Delivery.

It should provide a local-private daily watchlist desk, split summary/chart/detail
delivery, bounded watchlist prefetch/materialization, visible refresh health, and
fast exact-symbol switching. It must reuse the existing watchlist/cache/runtime
engines, preserve source truth, and avoid hosted auth/billing or an unbounded
background fan-out.

