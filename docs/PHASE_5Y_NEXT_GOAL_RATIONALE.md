# Phase 5Y Next Goal Rationale

Updated: 2026-07-01

## Decision

Proceed to Phase 5Z: Authoritative Market Discovery And Heatmap Breadth.

## Why This Is Next

Phase 5Y materially improved the War Map journey. The largest user-visible benchmark
gap highlighted by the user is now Finviz-style discovery:

- the current equity universe is a bounded local registry;
- taxonomy is static and not authoritative index membership;
- the heatmap is useful but not yet broad, hierarchical or benchmark-grade;
- breadth, valuation, country/industry and liquidity coverage remain thin;
- supported symbol continuity is wider than the heatmap coverage, but not universal.

The supplied `finviz.PNG` and heatmap reference, plus clean-room behavior research
from OpenStock, yfinance and the existing FinanceDatabase audit, make this a well
evidenced next vertical slice.

## Phase 5Z Completion Target

Deliver one daily-use discovery journey:

```text
Market Map
-> authoritative/free-first universe and taxonomy status
-> sector/industry/country drilldown
-> performance/size/liquidity/valuation/freshness filters
-> transparent rank and treemap
-> selected symbol evidence
-> supported symbol workstation
-> return with map state preserved
```

The phase must prove online, cache and controlled-offline behavior, preserve nulls,
avoid fabricated membership or fundamentals, capture inspected desktop/mobile
screenshots, and keep direct external adoption within exact license boundaries.

