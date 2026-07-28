# Phase 6L Security And Isolation Report

Updated: 2026-07-10

## Controls

- Tenant and user identity come only from the resolved server session.
- Client-supplied identity fields are rejected before queueing.
- Account mutations require same-origin and CSRF; proxy bodies remain 16KB.
- Queue rows and audit reads are tenant-qualified.
- Public queue rows omit snapshot body, tenant/user identity, and auth material.
- Sync snapshots remove credentials, secrets, tokens, local paths, private
  notes, review notes, watch reasons, and raw metadata fields.
- Idempotency keys bind to a snapshot fingerprint; reuse with a changed payload
  fails.
- Offline replay uses bounded exponential backoff, five-attempt circuit state,
  generic error codes, and no raw provider/auth exception.
- No remote write occurs before explicit first-sync consent.
- No silent last-write-wins occurs on equal-version mismatch or deletion.

## Evidence

- Anonymous sync read returns 401.
- Missing CSRF returns 403.
- Account A queues one mutation; Account B sees pending 0 and receives 404 when
  guessing A's mutation ID.
- Deterministic outage retains pending state; recovery applies once; a later
  equal-version content mismatch becomes conflict and is not overwritten.
- Optional Supabase migrations are payload-free and RLS-first.
- Browser bundle, public payload, fixtures, screenshots, and release inspection
  must not contain secret-class environment values.

## Residual Risk

SQLite isolation is application-enforced and suitable only for local
conformance. Hosted database isolation, real session revocation, database role
grants, backups, and production incident response remain unproven.

