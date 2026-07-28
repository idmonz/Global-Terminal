# Phase 6N Execution Plan

Updated: 2026-07-14
Status: completed

## Objective

Deliver one explicit, source-backed saved-Watchlist observation run that
materializes validated snapshots and feeds the Phase 6M Attention Desk without
adding provider calls to triage interactions.

## Planned Work

- [x] Re-read durable goal, Phase 6N prompt, harness, skills, and Phase 6M proof.
- [x] Recheck Supabase owner-access branch and rerun all 28 external audits.
- [x] Write failing lifecycle, quota, source-clock, partial/LKG, isolation, and zero-triage-call tests.
- [x] Implement one bounded run -> atomic snapshot -> material diff -> Attention review journey.
- [x] Prove live/cache/stale/unavailable truth, cancellation, recovery, performance, privacy, and security.
- [x] Capture and inspect versioned desktop/mobile run and failure states.
- [x] Run full release gates and select the next goal from measured evidence.

The approved-machine handoff produced a real `phase6n.visual.v1` summary, 23
personally inspected screenshots, and an independent verifier pass. The 390px
first material row appears at y=720; ProductNav is 168px; focus/live-region,
failure/recovery, A/B isolation, exact return, zero-provider-call, and
no-overflow assertions pass. The final 1,032-test suite, benchmark, web/runtime,
release, and all-28 external audits pass. Hosted Phase 6N persistence remains
an explicitly unavailable branch; it is not required for the scoped local-first
completion and is carried forward as a commercial-platform dependency.
