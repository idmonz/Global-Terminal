# Phase 6N Implementation Report

Updated: 2026-07-15

## Outcome

Phase 6N delivers a local-first, explicit saved-Watchlist observation run that
materializes validated source evidence before the Phase 6M Attention Desk
reviews it. It does not turn page loads or triage actions into provider calls.

The implemented journey is:

```text
Attention Desk
-> inspect last run, session policy, provider budget, and source health
-> explicitly refresh one bounded saved Watchlist
-> queued/running/partial/completed/cancelled lifecycle
-> validate and atomically persist snapshots
-> compare only compatible observations
-> render material changes in Attention
-> open exact source evidence and return to the prior review state
```

## Product And Runtime Changes

- `lib/watchlist_observation_runs.py` owns planning, stable idempotency,
  cancellation, source-clock separation, quota accounting, validation, atomic
  persistence, partial/LKG recovery, comparable diffs, and Attention context.
- `lib/research_workspace_schema.py` advances the local research schema to
  version 14 with tenant-scoped run, snapshot, quota, and audit records.
- `supabase/migrations/20260714230000_phase6n_observation_and_hosted_hardening.sql`
  is deployed to the linked project. Remote migration history, 18-table schema,
  RLS, least-privilege grants, anonymous denial, and local functional isolation
  and password-authenticated hosted A/B observation CRUD/RLS are verified.
- `lib/attention_desk.py` consumes stored observation context without making a
  provider request.
- `lib/api_contracts.py` and `backend/api/app.py` expose versioned JSON-safe
  account run/list/detail/snapshot/cancel surfaces.
- the bounded same-origin Next account proxy rejects unapproved paths and does
  not accept client-selected tenant identity.
- `AttentionDesk.tsx` adds an explicit refresh command, progress/cancel state,
  last-completed truth, provider budget, recovery state, and material-change
  count to the real product journey.

## Operational Bounds

- manual refresh only; no broad automatic polling;
- maximum five symbols per product run;
- maximum 16 planned provider operations;
- maximum provider concurrency two;
- stable per-tenant/list/day idempotency prevents duplicate same-day work;
- configured, contacted, cache, stale, partial, unavailable, and fresh remain
  separate states;
- quote/market observation, retrieval, attempt, completion, and Attention
  checkpoint clocks remain separate;
- initial Attention SSR/RSC transfer is capped at ten rows while preserving
  `total_row_count`; measured HTML is 89,554 bytes.

## Atomic And Recovery Semantics

A completed run commits a validated snapshot set atomically. A partial run may
commit only valid rows and records each missing capability. Invalid provider
output is rejected with generic errors. Provider failure preserves the prior
valid observation as explicitly stale/LKG evidence; it never inserts an empty
or fake live row. Retrieval-clock-only movement is nonmaterial.

## Scope Truth

This phase completes the implementation and controlled runtime evidence for the
local-first observation journey. The Phase 6N Supabase schema is now deployed,
and its hosted database boundary now passes the secure password-authenticated
Account A/B harness. Product runtime persistence remains local-first until the
hosted repository adapter and recovery drill pass. The approved-machine
handoff subsequently closed the 390px,
failure/recovery, account, and drilldown visual gate with 23 inspected images
and an independent verifier pass. The durable product-parity goal remains
active because hosted operations and benchmark-grade breadth are still absent.
