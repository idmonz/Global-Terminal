# Phase 5Z Implementation Report

Updated: 2026-07-01

## Product Outcome

Market Map is now a source-aware discovery workflow rather than a bounded 60-row
rank panel:

```text
Market Map -> sector/industry hierarchy -> metric/filter exploration
-> selected evidence -> Symbol Workstation -> restored discovery state
```

## Runtime

- `lib/runtime_cache.py`: text TTL/stale/single-flight fetch support.
- `lib/market_universe.py`: official Nasdaq/other-listed parser and listing contract.
- `lib/market_discovery.py`: one broad Yahoo market snapshot reused for financial
  discovery rather than duplicated provider calls.
- `lib/market_map_screener.py`: four-layer merge, provenance, exclusions, null-safe
  rank eligibility, and `market_map_screener.v2`.
- `backend/api/app.py`: compact JSON response path for the large read-only map
  envelope.

## Web Product

- 14 composable filters;
- sector -> industry -> symbol drilldown;
- sector, industry, or flat grouping;
- market-cap, volume, or equal sizing;
- 1D return, 1M return, or relative-volume coloring;
- explicit screened/listed/taxonomy/excluded/index-claim strip;
- selected-symbol membership, taxonomy, history, and rank evidence;
- local URL state changes without provider reload;
- supported AAPL workstation round trip;
- honest unsupported workstation and unknown-symbol state.

Desktop filters use a visible two-row grid. Mobile keeps compact horizontally
scrollable evidence and filter strips so the map section begins in the first
viewport without page-level overflow.

## Performance

Baseline:

- 60 rows;
- approximately 0.99 MB;
- cold request 4.18 seconds;
- repeated request 1.11 seconds.

Final:

- 137 rows and 1.87 MB;
- fresh-process cold request 6.38 seconds;
- cached contract composition approximately 0.25-0.40 seconds;
- final local HTTP response approximately 0.43-0.46 seconds using `curl`;
- no request-time per-symbol provider fan-out;
- filter, hierarchy, metric, and selection changes are client-side.

The larger response should be materialized and compressed in the next phase rather
than expanded through more synchronous providers.

## Truth Boundaries

This phase does not claim real-time quotes, complete US-market coverage,
authoritative index membership, licensed fundamentals, or current sector taxonomy.
It does not add orders, recommendations, broker actions, auth, billing, or hosted
persistence.
