# Phase 5Z Next Goal Rationale

Updated: 2026-07-01

## Evidence

Phase 5Z removed the old 60-row ceiling and made listing, observation, history, and
taxonomy authority visible. It also reduced cached HTTP response time below the
1.5-second local budget.

The largest next bottlenecks are now:

1. synchronous cold composition still takes roughly 6 seconds;
2. the 1.87 MB envelope will not scale to a full US universe;
3. taxonomy covers 60 of 137 rows and is not authoritative/current;
4. index membership remains explicitly unavailable;
5. the web lacks background refresh, durable shared snapshots, conditional HTTP
   caching, and observable provider jobs;
6. SEC company facts and earnings/calendar depth remain missing from the linked
   Symbol Workstation.

## Selected Next Phase

Phase 6A: Materialized Market Snapshot And Company-Facts Depth.

Build a background-refresh/read-optimized market snapshot boundary first, then add
official SEC company facts and earnings/calendar availability without request-time
N+1 calls. This unlocks wider discovery while improving the Market Map ->
Workstation daily journey.

## Why Not Auth/Billing First

Auth and billing are required for a commercial release, but monetizing a slow,
partially authoritative discovery surface would preserve the wrong bottleneck.
Phase 6A should establish materialization, observability, and company-facts value;
Phase 6B can then add hosted identity, entitlements, and private persistence over a
more credible product core.

## Required Next Proof

- cold web request serves a stored snapshot within a local target budget;
- refresh jobs expose last success, duration, row counts, errors, and stale state;
- payload size is reduced through summary/detail separation and HTTP caching;
- SEC facts preserve units, periods, forms, filed dates, and missingness;
- earnings/calendar claims are provider-backed or explicitly unavailable;
- online/stale/offline desktop/mobile evidence and full release gates pass.
