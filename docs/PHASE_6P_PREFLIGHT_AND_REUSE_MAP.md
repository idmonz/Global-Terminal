# Phase 6P Preflight And Reuse Map

Updated: 2026-07-15

Closure note: this section preserves the pre-edit baseline. The later
2026-07-16 owner handoff passed Phase 6O hosted A/B, Phase 6P hosted document
A/B, and Phase 6P fresh-repository product recovery. See
`docs/PHASE_6P_HOSTED_ACCOUNT_RECOVERY_EVIDENCE.md`.

## Phase Contract

Phase 6P cuts one account-owned research journey from process-local test
identity to a real Supabase password session and tenant-owned hosted
repository. The journey must restore after sign-out/sign-in, preserve an
honest local cache during an outage, reject cross-tenant access, surface
optimistic conflicts, and reconcile without duplicate audit evidence.

Hosted scheduling, external notification delivery, billing, broker actions,
and autonomous behavior remain outside this phase.

## Verified Starting Evidence

- `review_workspace/phase6n_hosted_rls_summary.json` exists and records
  `phase6n.hosted.rls.v1` as passed.
- The Phase 6N matrix proves distinct Account A/B identities and tenants,
  observation-run/snapshot/quota/audit isolation, cross-parent rejection,
  optimistic conflict behavior, immutable audit creation, and audit retention
  after bounded parent deletion.
- Phase 6O local PostgreSQL RLS, remote anonymous denial, product tests,
  performance, and visual evidence pass.
- `review_workspace/phase6o_hosted_rls_summary.json` is not present. The
  password-authenticated five-table Alert Manager A/B gate therefore remains
  pending and must not be reported as passed.
- `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` are configured. No
  service-role or secret key is required or configured for ordinary CRUD.
- The pre-edit web fixture/runtime contract test passes.
- The pre-edit release archive contains 1,776 entries including its manifest.
- The pre-edit full Python run is recorded in the active plan when complete.

## Reuse

| Existing boundary | Phase 6P use |
|---|---|
| `SessionManager`, `gt_session`, `gt_csrf` | Preserve opaque HttpOnly session and double-submit CSRF behavior for local QA; add a hosted session broker behind the same cookie boundary. |
| Same-origin Next account proxy | Preserve path allowlisting, body limits, generic offline response, cookie forwarding, and no-store behavior. |
| `TenantResearchRepository` and local stores | Keep the current domain behavior and SQLite implementation as the local cache/offline continuity layer. |
| `TenantResearchPersistence` and `TenantResearchSyncCoordinator` | Extend the real hosted adapter and reuse explicit consent, idempotency, conflict, bounded queue, retry, and audit semantics. |
| Watchlist, Attention, observation, and Alert Manager contracts | Preserve payload shapes and exact source/freshness/caveat behavior. Do not move PostgREST logic into React. |
| Phase 6J-6O Supabase migrations | Preserve tenant membership, RLS, composite parent integrity, and immutable audit evidence. Add an additive repository migration only. |
| Phase 6N/6O visual handoff | Reuse production-server launch, browser telemetry, desktop/390px capture, focus, live-region, overflow, and independent summary verification patterns. |

## Retire Or Narrow

| Existing behavior | Decision |
|---|---|
| `SupabaseTenantResearchPersistence` always raises `HostedPersistenceUnavailable` | Replace configuration-only behavior with a user-JWT-bound repository. Unauthenticated/local-test contexts remain unavailable by design. |
| `persistence_provider_health()` always reports `contacted=False` | Make health session-aware and record configured, contacted, authenticated, read, write, conflict, outage, and recovery clocks separately. |
| UI copy that says hosted authentication is unavailable | Replace only when a real session succeeds. Local QA copy remains explicit and separately gated. |
| Process-local aliases as the primary sign-in experience | Keep behind `GLOBAL_TERMINAL_LOCAL_AUTH_ENABLED` for QA; add email/password Supabase sign-in as the commercial path. |
| Silent assumption that local state equals restored hosted state | Require a remote document version/fingerprint and an explicit restore/reconciliation result. |

## Selected Architecture

1. FastAPI authenticates with Supabase using the publishable key and stores
   access/refresh tokens only inside a process-local server session addressed
   by the existing opaque HttpOnly cookie. Tokens never enter public payloads,
   URLs, screenshots, fixtures, or browser storage.
2. User identity is verified against Supabase Auth. Tenant and role are derived
   by querying the authenticated user's membership; client-provided user or
   tenant identifiers are rejected.
3. A bounded account research document persists a tenant-local projection of
   the existing Watchlist, Attention, observation, and Alert Manager SQLite
   rows. The document uses optimistic aggregate versions, idempotency receipts,
   immutable fingerprint-only audit, RLS, and server-derived ownership.
4. Existing local domain stores remain the active business-logic engine and
   last-known-good cache. A successful hosted sign-in hydrates only that user's
   tenant rows. A local mutation is captured and pushed through the hosted
   repository; outage/conflict state is explicit and queued, never called
   remotely saved.
5. Restore/import validates a strict table and column allowlist, strips all
   identity fields from hosted payloads, reinjects identity from the verified
   session, checks bounded size/counts, validates parent references, and never
   deletes immutable audit rows during reconciliation.

## Threat And Failure Model

- A forged tenant/user field in any request or hosted document is rejected.
- An access token is never accepted from a browser header or body.
- Expired access tokens are refreshed server-side; a failed refresh invalidates
  the opaque session and returns a generic signed-out state.
- A stale document version produces a conflict and retains the local mutation
  for explicit reconciliation.
- A network/database outage keeps the last valid local projection available,
  records no remote-success clock, and queues at most the documented bounded
  mutation count.
- Replayed idempotency keys return the original result and must not duplicate
  document, trigger, run, receipt, or audit rows.
- Account B cannot select, mutate, restore, or infer Account A's document or
  audit rows.
- No service-role key is used for login, repository reads/writes, restore, or
  conformance.

## Official Reference Decisions

- Supabase Auth access tokens are short-lived JWTs and refresh tokens rotate;
  session refresh must be serialized and tokens must not be logged.
- Authorization relies on verified user identity plus PostgreSQL RLS using
  `auth.uid()`, not user-editable metadata or a client-selected tenant.
- Free projects need an operator-run logical backup because paid daily-backup
  retention must not be assumed.

## Done Evidence

The phase is not complete until focused/full tests, real hosted A/B and
new-session restore evidence, outage/recovery and conflict proof, a private-safe
backup/restore drill, desktop/mobile screenshots, performance/privacy gates,
release inspection, and the final external audit all pass.
