# Phase 6G Snapshot Diff Contract

Updated: 2026-07-03

## `research_snapshot_diff.v1`

The contract compares two completed snapshots from the same watchlist without
provider, network, or broad-universe work.

Each change contains:

- stable `change_id`, symbol, change type, field, and severity;
- before/after value and unit;
- previous/current snapshot IDs and clocks;
- provider, source URL, source status, fetched/as-of clock, confidence, caveat,
  and data gap for both sides where available;
- observation text that does not infer causality or recommend action.

Change types are `symbol`, `price`, `performance`, `fundamental`, `event`,
`news`, and `source-status`.

## Materiality

- Price: at least 1% relative movement.
- Performance: at least 1 percentage point.
- Fundamental numeric value: at least 5% relative movement.
- Event schedule/type: any normalized date/type change.
- Exact news: new strict source/title identity only.
- Source status: any normalized degradation or recovery.
- Added/removed symbols: always material.

Null is distinct from zero. Numeric comparisons require two finite values.
Thresholds are calculation policy, not investment significance.

## Invariants

- Cross-list comparisons are rejected.
- Incompatible or empty snapshots produce an explicit unavailable state.
- News repeats are deduplicated by canonical source URL or normalized
  title/published identity.
- Stable IDs hash normalized semantic before/after content, not transient
  timestamps.
- Ordering is deterministic by severity, symbol, type, field, and ID.
