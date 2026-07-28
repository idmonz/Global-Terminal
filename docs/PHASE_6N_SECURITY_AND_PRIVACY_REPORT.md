# Phase 6N Security And Privacy Report

Updated: 2026-07-14

## Enforced Boundaries

- account identity and tenant scope derive from the server session;
- observation run, snapshot, cancellation, export, and audit reads are
  tenant-scoped;
- POST operations retain CSRF, same-origin, bounded-body, idempotency, and rate
  controls;
- cancellation ownership and optimistic version checks are server-side;
- provider bodies, credentials, private notes, holdings, paths, sessions, user
  IDs, and tenant IDs are excluded from fixtures and public payloads;
- generic error codes are stored instead of raw provider bodies;
- Attention compose, filter, review, acknowledge, snooze, policy, checkpoint,
  and return navigation make zero provider calls;
- provider outage does not trigger a retry on page load.

## Supabase Truth

The linked Supabase project is reachable through the authenticated CLI. On
2026-07-14, the Phase 6J-6M remote schema was backed up and reconciled with the
local migration chain, then the Phase 6N observation migration was deployed.
All five migration versions now align locally and remotely.

The remote project exposes 18 `global_terminal_*` tables with RLS enabled.
There are zero anonymous product-table grants. The four Phase 6N endpoints are
present and reject anonymous reads with HTTP 401. Runs, snapshots, quota rows,
and audit rows have reviewed least-privilege grants; child rows use composite
tenant/owner/run foreign keys; authenticated clients cannot insert audit rows.
The full local chain passed a clean reset and a real-role A/B isolation,
optimistic-conflict, cascade, and audit-retention test.

On 2026-07-15, `scripts/test-phase6n-observation-rls.ps1` passed all 27 checks
using two real password sessions without a service-role credential. Account B
could not read, update, delete, or cross-insert Account A data; composite parent
integrity, stale-version handling, audit immutability, audit retention, and
post-delete isolation passed with zero provider calls. Backup restore, session
revocation, hosted outage/recovery, and latency evidence remain separate open
gates from the accepted local-first Phase 6N contract.

## Release Privacy Repair

The first candidate archive scan found one exact `SUPABASE_URL` occurrence in
a historical evidence document. That document was redacted, and manual RLS QA
scripts were changed to require local environment variables rather than
hard-coded test emails or UUIDs. `.env.example` keeps those QA names as
commented placeholders so they are never active release configuration.

`tests/test_phase6n_release_privacy.py` prevents regression. The final release
must pass exact-value and forbidden-member scans before it is accepted.

## Residual Risks

- authenticated hosted A/B RLS is verified for the new Phase 6N tables;
  backup restore and outage recovery remain unverified;
- free/delayed public market sources are not licensed exchange-real-time feeds;
- no background worker, notification delivery, broker action, or autonomous
  trading is enabled;
- backup restore, recovery, and scheduled-worker evidence remain open; hosted
  A/B conformance, schema deployment, and local visual/release gates are
  complete.
