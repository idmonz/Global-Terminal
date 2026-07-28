# Phase 6F Next Goal Rationale

Updated: 2026-07-03

## Decision

Select **Phase 6G: Research Snapshot Diff, Refresh Operations, And Alert
Readiness**.

## Evidence

Phase 6F makes one manual bounded refresh useful, but daily value still depends
on the user noticing when the saved snapshot is old and manually comparing
events. The materialization job already has budget, cache/LKG, duration,
overlap, and next-safe-refresh evidence. The next highest-value step is to turn
that evidence into a local operational loop and source-preserving change set.

## Required Outcome

- compare the latest two same-list snapshots without recomputing providers;
- identify material price/fundamental/event/news/source-status changes;
- expose a compact "what changed" inbox with before/after evidence;
- add an explicit local scheduler/readiness boundary, health, kill switch, and
  runbook;
- allow opt-in local notification previews only after dedupe/cooldown tests;
- keep hosted delivery, auth, billing, broker actions, and personalized advice
  unavailable.

## Rejected Alternatives

- Broad UI expansion would dilute the now-complete recurring Watchlist journey.
- Hosted auth/billing is premature before refresh and change operations are
  observable.
- Real alert delivery is premature before deterministic diff, dedupe, cooldown,
  and failure retention exist.
- More per-symbol providers would exceed the free-first budget before the
  current provider set is operationally reliable.

The next prompt is maintained in `docs/NEXT_ROADMAP_EXECUTION_PROMPT.md`.
