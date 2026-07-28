# Phase 6L Persistence Contract

Updated: 2026-07-10

## Boundaries

`TenantResearchRepository` is the unchanged Phase 6K account boundary. It owns
watchlists/items, import consent receipts, rules, inbox states, optimistic
versions, export, deletion, and the public desk contract. FastAPI now references
this Protocol rather than the concrete SQLite class.

`TenantResearchPersistence` is the narrower synchronization adapter. It exposes:

```text
health()
snapshot(server_derived_context)
apply_snapshot(server_derived_context, bounded_snapshot, idempotency_key)
```

Implementations:

- `SQLiteTenantResearchPersistence`: local source-of-truth projection;
- `DeterministicFakeTenantResearchPersistence`: conformance, outage, retry, and
  conflict tests only;
- `SupabaseTenantResearchPersistence`: fail-closed provider boundary until live
  auth/RLS proof passes.

## Snapshot Contract

`tenant_research_sync.v1` contains at most 25 resources and 30,000 UTF-8 bytes.
Resources are deterministic `watchlist`, `watchlist-item`, `rule`, `inbox`, or
`consent-receipt` records with opaque ID, version, deletion flag, sanitized
payload, and fingerprint.

The projection removes identity, credentials, local paths, private notes,
review notes, watch reasons, raw metadata fields, and secret/token-like keys.
It preserves public symbol identity, source URL/status, observation/retrieval
clocks, evidence, rules, and review state. Market-provider calls are always 0.

## State Contract

Public sync state is one of:

- `hosted-unavailable`;
- `pending`;
- `synced` only for a verified adapter;
- `conflict`;
- `offline` on replay results.

Reconciliation classifies every key as `same-version`, `local-newer`,
`remote-newer`, `conflict`, or `deletion`. It reports
`silent_last_write_wins=false`; conflict and deletion require explicit review.

## API Surface

- `GET /api/account/research-desk/sync`
- `GET /api/account/research-desk/sync/preview`
- `POST /api/account/research-desk/sync/queue`
- `POST /api/account/research-desk/sync/replay`
- `DELETE /api/account/research-desk/sync/queue/{mutation_id}`

All mutations require an authenticated server-derived session, same origin,
CSRF, bounded body, and tenant-qualified database operation.

