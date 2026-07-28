# Phase 6N External, Benchmark, And User Evidence

Updated: 2026-07-14

## Final External Audit

The deterministic final audit under
`review_workspace/external2_analysis/phase6n-final/` covers every requested
archive under `external (2)/external`:

- 28 archives;
- 51,305 ZIP entries;
- 38,623 indexed non-vendored text/code files;
- 8,742,912 indexed non-vendored lines;
- 24 traceable feature candidates;
- license matrix: 18 direct-use allowed, six behavior-only, three needs review,
  and one blocked.

A separate full archive-text scan counts 39,622 text candidates,
10,596,233 raw lines, and 249,590 symbols with zero read errors. It
intentionally includes files excluded from the clean-room non-vendored line
index; the two metrics are complementary, not contradictory.

No restrictive, unclear, NASA, AGPL, or blocked source/assets were copied into
the commercial product. Direct-use eligibility was not treated as a reason to
copy when a project-native implementation was clearer.

## Relevant Behaviors Studied

- TradingView: watchlists centralize symbols, key metrics, news, fundamentals,
  technicals, grouping, and list-wide alerts; session settings affect alert
  evaluation.
- OpenBB: provider/command separation and explicit source choice support a
  source-aware workstation.
- World Monitor/worldview: layer/source health and time-state truth are more
  valuable than unlabeled markers.
- Finviz and supplied heatmap references: dense first-viewport scanning and
  fast drilldown matter more than decorative cards.
- Bloomberg-like and Korean-terminal references: compact status strips,
  keyboard-friendly actions, exact clocks, and persistent context reduce
  repeated checking.
- external Watchlist, cache, provider, and operations candidates reinforced
  bounded runs, idempotency, LKG continuity, and inspectable progress.

Current official product research also confirms the next retention gap:
TradingView exposes per-symbol watchlist alert evaluation, frequency,
expiration, manager state, and a trigger log; Finviz exposes compact chart
alerts and management; World Monitor combines custom monitors, new/seen state,
and periodic snapshots; Supabase Cron supplies a bounded hosted scheduling/run-
history reference. See `docs/PHASE_6N_NEXT_GOAL_RATIONALE.md` for direct links
and the clean-room decision.

## User Problem And Product Response

The selected problem is not simply "send more alerts." Users already face
stale data, unclear clocks, free-tier quota exhaustion, repeated manual
checking, duplicate refreshes, and alert fatigue. Phase 6N responds with one
explicit bounded run, visible due-work/quota/source truth, stable replay,
atomic evidence, material diffs, and zero additional provider calls while
triaging.

This is narrower than TradingView's always-on list alerts but more explicit
about free-provider limits and source provenance. Notification delivery,
arbitrary alert formulas, broad always-on scheduling, and licensed streaming
remain future work rather than simulated parity.

## Bottleneck Decision

The Phase 6N implementation, data path, responsive visual matrix, and release
gate are closed. The next measured product bottleneck is fragmentation: the
repository has alert rules, evaluators, stores, preview routes, and scheduler
helpers, but no coherent commercial Alert Manager that converts a bounded due
observation into a tenant-safe, source-aware in-app trigger history.

Hosted observation persistence remains a separate credential and RLS-
conformance gate. Phase 6O must preserve that truth rather than hide it.
