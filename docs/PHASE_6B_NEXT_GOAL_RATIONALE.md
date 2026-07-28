# Phase 6B Next Goal Rationale

Updated: 2026-07-01

## Evidence

Phase 6B raised useful discovery from 137 to 333 official-listing-matched rows,
made all displayed sector classifications source-aware, retained 60 reviewed
industries, and added materialized scheduling/history while preserving performance.

The next largest user-value defect is now the discovery-to-analysis boundary:

1. many of the 333 results do not have an activated Symbol Workstation route;
2. only the original bounded history set has complete technical/rank factors;
3. broad selected-symbol detail is stored but not yet loaded on demand into a full
   chart/financial/news workstation;
4. watchlist activation and source-aware filing drilldown are narrow;
5. mobile breadth is useful but extremely long.

## Selected Next Phase

Phase 6C: Dynamic Broad-Symbol Workstation Activation.

It should allow any supported identity selected from the materialized Market Map
to open an exact-symbol, provider-backed, cached workstation without expanding the
static registry or leaking another symbol's fixture. It should add on-demand
history/technical/financial/news capability, preserve origin state, and keep
unknown/provider-failure states honest.

