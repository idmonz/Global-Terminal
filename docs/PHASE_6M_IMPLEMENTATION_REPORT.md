# Phase 6M Implementation Report

Updated: 2026-07-14

## Delivered

- `lib/attention_desk.py` implements normalization, materiality, source-aware
  dedupe, deterministic ranking, daily digest, filters, policy, checkpoints,
  tenant review state, audit, conflict, snooze, expiry, and undo.
- research schema version 13 adds indexed Attention policy, checkpoint, review,
  and audit storage.
- API contracts, FastAPI routes, same-origin Next account proxy, fixture export,
  and route manifest expose `attention_desk.v1` without Streamlit logic.
- `AttentionDesk.tsx` is a first-class product surface linked from Market Home
  and Watchlist Desk.
- Analyst, News, Daily Brief, and War Map preserve bounded origin/return state.
- Supabase migration `20260711234452_phase6m_attention_and_rls_hardening.sql` adds the
  Attention schema and replaces ambiguous tenant policies with qualified,
  fail-closed policy expressions.

## Daily Journey

```text
open Attention Desk
-> read bounded digest and since-last-review counts
-> filter prioritized stored evidence
-> inspect source truth and separate clocks
-> open exact Analyst, News, Brief, or Map evidence
-> return to the same review state
-> review, acknowledge, snooze, or change policy
-> advance a private review checkpoint
```

The first desktop viewport contains digest, review counts, filters, prioritized
rows, source truth, and actions. The 390px layout puts the first high-severity
row at y=787 without page-level horizontal overflow. Product navigation remains
168px on desktop and becomes a contained horizontal rail on mobile.

## Honest Limits

The linked hosted Supabase project now contains 18 Phase 6J-6N product tables.
Phase 6M evidence records successful tenant bootstrap, basic CRUD, and A/B RLS
denial checks. On 2026-07-14, Account A/B bootstrap and tenant separation were
reconfirmed, migration history was reconciled, and the reviewed Phase 6N
observation migration was deployed from the CLI after schema/data backups.

This is not full hosted verification. Schema, least-privilege grants, all-table
RLS, anonymous denial, and local functional A/B isolation are verified, but the
new Phase 6N tables now pass the password-authenticated hosted A/B harness,
including conflict, composite-parent, audit-immutability, deletion, and
cross-tenant denial paths. Session revocation, backup restore, bounded
export/deletion, hosted recovery, and latency/SLO evidence remain open.

The Attention Desk does not create fresh observations. It reviews saved
evidence. Source-backed observation materialization is the next product
bottleneck and Phase 6N scope.
