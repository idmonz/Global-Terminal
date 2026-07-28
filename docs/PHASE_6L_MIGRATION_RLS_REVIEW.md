# Phase 6L Migration And RLS Review

Updated: 2026-07-10

## SQLite Schema 12

Phase 6L adds two local-only tables:

- `tenant_sync_mutations`: tenant-qualified idempotency, sanitized snapshot,
  byte/resource bounds, state, retries, generic error code, and remote revision;
- `tenant_sync_audit`: bounded event type/status/detail without public identity,
  raw auth body, private notes, or secrets.

Indexes cover tenant/state/creation, retry scheduling, and audit chronology.
Existing Phase 6K account tables and payloads remain additive and compatible.

## Optional Supabase Readiness

`supabase/migrations/20260710164600_phase6k_tenant_research.sql` remains the account
record model. `20260710212959_phase6l_sync_readiness.sql` adds payload-free sync
receipts and deletion tombstones. It intentionally stores no snapshot body.

Static tests require:

- RLS enabled on both Phase 6L tables;
- `authenticated` policies using `(select auth.uid())`;
- tenant membership checks and owner-bound writes;
- tenant-qualified uniqueness and indexes;
- no browser/server secret in SQL;
- no hosted-success marker.

The approach follows current Supabase RLS guidance on exposed tables, explicit
roles, indexed policy columns, and `auth.uid()`:
<https://supabase.com/docs/guides/database/postgres/row-level-security>.

## Not Proven

Static SQL is not live RLS evidence. The following remain required before the
state can change from unavailable:

1. disposable Account A/B auth sessions;
2. positive CRUD and negative cross-tenant list/detail/update/delete/export;
3. expired/revoked/anonymous rejection;
4. migration rollback, backup/restore, cascade, tombstone, and cleanup;
5. outage/recovery, conflict, and measured hosted latency;
6. secret/bundle/log/screenshot/release scan.
