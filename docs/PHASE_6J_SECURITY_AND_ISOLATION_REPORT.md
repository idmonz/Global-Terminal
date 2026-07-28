# Phase 6J Security And Isolation Report

Updated: 2026-07-10

## Proven Controls

- Server sessions, not JSON bodies, derive user and tenant IDs.
- Every preference query includes the authoritative tenant.
- Account B cannot get, enumerate, delete, or export Account A's record.
- A client-supplied tenant/user field is rejected with HTTP 422.
- Mutations require exact same origin, session-bound CSRF, and expected version.
- A stale write returns HTTP 409 and the UI displays recovery guidance.
- External Origin returns 403; unsafe return URL returns 422; traversal returns
  404 in production proxy evidence.
- Sign-in rotates session identity; sign-out revokes and clears cookies;
  expiry and revocation are unit-tested.
- Public payload redaction removes tokens, cookies, service keys, and paths.
- Session cookie is HttpOnly/SameSite Lax; CSRF cookie is SameSite Strict and
  intentionally browser-readable; production enables Secure through config.

## Isolation Evidence

Repository and HTTP tests use independent Account A/B tenants. Production
Chrome evidence saved Account A's 64% layout, restored it after navigation,
generated a real concurrent write conflict, signed out, signed into Account B,
and observed no Account A preference. Account B's attempted tenant override
returned 422.

## Not Proven

Supabase URL and keys were absent. Hosted RLS, recovery, backups, SMTP/OAuth,
multi-device sync, production cookie/TLS, and cloud incident response were not
live-tested and are not claimed.
