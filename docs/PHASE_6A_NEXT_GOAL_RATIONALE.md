# Phase 6A Next Goal Rationale

Updated: 2026-07-01

## Evidence

Phase 6A removed synchronous broad composition from successful web reads, reduced
the first-paint payload by roughly 60%, met the 500 ms local read budget, and added
official SEC facts plus earnings/calendar truth.

The largest remaining product bottlenecks are:

1. discovery breadth is 137 rows, far below broad-market screeners;
2. taxonomy covers only 60 rows and remains local static/proxy;
3. refresh is manual CLI operation rather than a proven scheduler;
4. refresh and provider health are local, not durable production telemetry;
5. selected-symbol detail is still thin compared with Finviz/TradingView/OpenBB;
6. index membership remains explicitly unavailable.

## Selected Next Phase

Phase 6B: Broad Market Universe, Reviewed Taxonomy, And Scheduled Refresh.

It should expand the materialized universe conservatively, reconcile SEC/Nasdaq
identity and reviewed classification evidence, add a tested local scheduler and
refresh history, and preserve the compact/read-optimized path.

Auth and billing remain later. They should not be placed over a universe that is
still too narrow and only partially classified.

