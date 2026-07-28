# Phase 6K Security And Isolation Report

Updated: 2026-07-10

## Proven Controls

- Every account read/write/delete/export is qualified by the session-derived
  tenant. Browser-supplied tenant/user fields are rejected.
- Account B receives empty collection results and 404 for Account A watchlist
  and inbox opaque IDs.
- Import requires explicit `consent=true`, selected candidate IDs, current
  preview identity, bounded idempotency key, and expected version.
- Same idempotency key returns the prior result. Stale writes return 409 and do
  not overwrite a newer tenant watchlist.
- Next proxy allowlists only exact account research route shapes, rejects path
  traversal, caps JSON at 16 KB, and forwards session/CSRF to the local API.
- Mutations retain Phase 6J exact-origin, CSRF, rotating session, revocation,
  expiry, and rate-limit controls.
- Inbox event dedupe, rule cooldown, expiry, kill switch, forward-only state,
  and referential cleanup run server-side.
- Public payload sanitization omits cookies, tokens, DB paths, authoritative
  tenant IDs, local private notes, and provider secrets.
- Optional Supabase tables enable RLS and require authenticated tenant
  membership for read/write/delete. The migration has not been applied.

## Evidence

- Repository and HTTP tests exercise A/B list, detail, delete, export, receipt,
  rule, and inbox isolation.
- Production Chrome observed Account B counts `0/0`; direct Account B reads of
  Account A watchlist and inbox returned 404.
- Invalid Origin returned 403, a 17 KB body returned 413, traversal returned
  404, and stale import returned 409.
- Sign-out returned 200 and the product returned to anonymous local mode.
- Release scan checked 15 configured environment values by exact bytes without
  printing them and found zero hits.

## Threats Still Open

Hosted Supabase auth/RLS, recovery, backup restore, TLS/cookie deployment,
multi-device conflict, abuse telemetry, production log access, and incident
response remain unverified. No hosted-success claim is made.
