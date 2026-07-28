# Phase 6J Identity And Tenancy Contract

Updated: 2026-07-10

`identity_tenancy.v1` separates four truths:

- anonymous/local workspace;
- explicitly enabled process-local test identity;
- tenant-scoped local-private preference storage;
- optional Supabase configuration that remains unverified until live RLS and
  recovery tests pass.

Authoritative `user_id` and `tenant_id` come from the server session. Mutation
bodies containing identity fields fail closed. Repository reads and writes use
tenant plus key/resource identity, opaque IDs, expected versions, bounded JSON,
CSRF, same-origin checks, rate limits, and session revocation.

The browser keeps its existing local layout independently. Nothing is uploaded
until the signed-in user explicitly chooses account save. Local test sessions
are process-local, expire, and are not production authentication.

The optional Supabase migration enables RLS on every exposed table and uses
membership policies. No Supabase SDK, hosted-success claim, checkout, payment,
broker action, or autonomous action is added in Phase 6J.
