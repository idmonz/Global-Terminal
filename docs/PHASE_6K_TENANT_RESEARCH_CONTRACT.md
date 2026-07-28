# Phase 6K Tenant Research Contract

Updated: 2026-07-10

`tenant_research_desk.v1` composes existing local Watchlist, saved Research
Snapshot, snapshot-diff, and alert-preview engines behind a separate account
ownership boundary. It does not duplicate provider retrieval.

## Journey

```text
anonymous local watchlist
-> lazy optional process-local sign-in
-> read-only 25-row import preview
-> explicit selected-row consent
-> versioned tenant watchlist and consent receipt
-> exact Analyst Workspace link with return context
-> opt-in saved-change rule
-> deduplicated tenant in-app inbox
-> reviewed -> acknowledged persistence
```

## Stored Resources

- `tenant_watchlists`: session-tenant-owned destination, source fingerprint,
  optimistic version, and opaque public ID.
- `tenant_watchlist_items`: exact identity, stable position, provider, source
  URL, source status, observation/retrieval clocks, and bounded evidence.
- `tenant_import_receipts`: tenant-scoped idempotency key, request fingerprint,
  preview identity, selected count, exclusions, and consent clock.
- `tenant_alert_rules`: opt-in, minimum severity, cooldown, expiry, last trigger,
  and optimistic version.
- `tenant_inbox_items`: deterministic dedupe key, exact change identity,
  evidence, source state, clocks, expiry, review, acknowledgement, and version.

The SQLite schema is additive v11. The optional Supabase migration mirrors the
ownership model with RLS policies but is readiness evidence only.

## Boundary Rules

- `tenant_id` and `user_id` always come from the server session.
- Client bodies containing identity fields fail closed.
- Preview is bounded to 25 rows, read-only, and performs zero provider calls.
- `watch_reason` and `metadata_json` are excluded from preview, receipt, export,
  URL, screenshot, and account copy.
- A repeated idempotency key returns the prior result; a newer resource with a
  different key and stale expected version returns conflict.
- Inbox transitions are forward-only: `new -> reviewed -> acknowledged`, with
  direct `new -> acknowledged` allowed. Acknowledged items cannot move back.
- Rule kill switch returns `suppressed`; expired rules return `expired` without
  creating an item. External delivery remains `unavailable`.
- Inbox retention is 90 days and consent receipt retention is 365 days in the
  contract. Hosted retention enforcement is not claimed.
- Deleting a watchlist transactionally deletes its tenant-owned items, receipt,
  rule, and inbox children.

## API Surface

Reads use no-store session context. Mutations additionally require exact same
origin, session-bound CSRF, bounded JSON through the Next proxy, rate limiting,
idempotency where applicable, and optimistic versions.

- `GET /api/account/research-desk`
- `GET /api/account/research-desk/imports/preview`
- `POST /api/account/research-desk/imports`
- `GET|DELETE /api/account/research-desk/watchlists/{opaque_id}`
- `PUT /api/account/research-desk/watchlists/{opaque_id}/rule`
- `POST /api/account/research-desk/watchlists/{opaque_id}/inbox`
- `GET|PATCH /api/account/research-desk/inbox/{opaque_id}`
- `GET /api/account/research-desk/export`

Outputs are research information only, not advice, recommendations, order
routing, broker action, or autonomous action.
