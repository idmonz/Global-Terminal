# Phase 6M Next Goal Rationale

Updated: 2026-07-13

## Evidence-Selected Next Phase

**Phase 6N: Source-Backed Observation Runs And Live Attention Materialization.**

Phase 6M solves attention fragmentation once evidence has been stored. Its
largest remaining product limitation is upstream: deterministic fixtures and
manually completed snapshots still carry too much of the daily queue. Users
need one bounded way to refresh a saved watchlist, observe run health, retain
last-known evidence during failure, and produce material diffs without a
provider request firing from every triage interaction.

Phase 6N should deliver one vertical journey:

```text
open Attention Desk
-> see last completed observation run and market-session policy
-> explicitly refresh one bounded saved watchlist
-> observe queued/running/partial/completed source health
-> atomically save source-clocked snapshots
-> compose new Attention rows from the completed run
-> review exact evidence with no additional provider calls
```

It must reuse existing Alpha Vantage, Finnhub, market snapshot, Watchlist,
runtime cache, provider-health, and Attention engines. Free-first quota budgets,
single-flight, partial completion, cache/stale fallback, cancellation, and exact
source clocks are completion gates. It must not add autonomous trading,
personalized advice, broad background polling, or fake live rows.

## Supabase Branch

If project-owner CLI/SQL access becomes available, run the hardened migrations
and real Auth A/B RLS conformance before changing hosted status. Otherwise the
observation-run journey remains local-first and hosted remains unavailable.

The durable benchmark goal remains active. Phase 6M does not establish hosted
commercial readiness or benchmark-grade parity.
