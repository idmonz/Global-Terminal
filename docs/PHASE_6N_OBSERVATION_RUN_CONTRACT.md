# Phase 6N Saved Watchlist Observation Run Contract

## Purpose

Phase 6N turns the saved Watchlist into an explicit, user-started observation workflow. One bounded run may retrieve source-backed evidence, commit a complete snapshot set, and expose material changes to Attention Desk. Reading or filtering Attention Desk always makes **zero provider calls**.

The contract is research-only. It never places orders, sends alerts, starts itself on page load, or claims exchange-calendar certainty that the runtime did not verify.

## Lifecycle

The only public run states are `queued`, `running`, `partial`, `completed`, `cancelled`, and `failed`.

- `queued`: accepted, validated, and waiting for its single-flight execution slot.
- `running`: bounded provider/cache work is in progress.
- `completed`: every promotable symbol snapshot was committed atomically.
- `partial`: usable rows were committed with explicit gaps and optional last-known-good recovery.
- `cancelled`: cancellation was accepted before promotion; no incomplete snapshot set is authoritative.
- `failed`: the run ended without promoting an incomplete set; the prior completed evidence remains authoritative.

One tenant may have at most one active run for a saved Watchlist. A stable idempotency key replays the same run instead of consuming provider quota twice.

## Clock Semantics

Every run and promoted row preserves separate clocks:

- `attempted_at`: when the runtime began an observation attempt.
- `observed_at`: when the source says the market or event value was observed.
- `retrieved_at`: when this runtime received or recovered the evidence.
- `completed_at`: when the atomic run outcome became terminal.

`retrieved_at` never substitutes for `observed_at`. Cache reuse can advance retrieval evidence without claiming a newer market observation.

## Quota And Session Policy

The default run is `market-aware`, limited to five symbols, at most sixteen bounded operations, two concurrent operations, 75 seconds, and a 250 KB public payload. Crypto is treated as continuous; equity session status is a timezone/weekday proxy unless an exchange calendar provider verifies it.

Alpha Vantage documents a free-service limit of **25 requests per day**. The planner reserves and records calls before execution and skips work when the local quota ledger cannot prove headroom. Finnhub receives a conservative local rate-window guard; a paid or account-specific allowance is never inferred from a key's presence.

`cache-only` performs no network operation. `force-bounded` remains subject to the same hard caps and quota ledger. Provider absence, rate limiting, stale evidence, and subscription restrictions are explicit outcomes, never synthetic live rows.

## Snapshot Promotion And Recovery

Snapshots are normalized, JSON-safe, provenance-bearing, and size checked before promotion. The store performs an **atomic** transaction: either the run metadata, all accepted snapshot rows, quota ledger changes, and audit event commit together, or none become authoritative.

On a bounded provider failure, the runtime may reuse the prior **last-known-good** snapshot for that tenant, list, symbol, interval, and range. Reuse is labeled with its original observation clock, current retrieval clock, source status, caveat, and data gap. Tenant A can never read Tenant B's run, snapshot, quota ledger, or audit rows.

## Attention Desk Boundary

Attention Desk consumes only committed observation rows and precomputed differences. Page load, sort, filter, review, snooze, acknowledge, checkpoint, polling, and drilldown composition make **zero provider calls**. Only the explicit `Refresh saved Watchlist` command can create a run.

Fixture mode is deterministic and disables refresh with `fixture-does-not-contact-providers`. Account/cache mode retains the last completed evidence when the observation worker or provider is offline.

## Security And Hosted Readiness

The local store is tenant scoped and optimistic-versioned. The API requires an authenticated same-origin session and CSRF token for mutations. Public payload sanitization rejects secret-like values and private paths. The Supabase migration enables row-level security, revokes anonymous access, grants authenticated access only, and binds every policy to `auth.uid()`.

Hosted persistence remains unavailable until an operator applies the reviewed migration and verifies RLS with two distinct authenticated users. Public Supabase keys are browser-safe only in combination with effective RLS; service-role credentials are never exposed to the web client.

## Evidence

- Alpha Vantage free-service limit: <https://www.alphavantage.co/support/>
- Finnhub API status and rate-limit semantics: <https://finnhub.io/docs/api/introduction>
- Supabase row-level security: <https://supabase.com/docs/guides/database/postgres/row-level-security>
