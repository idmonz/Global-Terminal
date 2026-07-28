# Phase 6P Execution Plan

Updated: 2026-07-16
Status: completed for the scoped hosted account repository and recovery cutover

## Objective

Cut one complete account research journey from local-test/process-local storage
to a real Supabase user session and tenant-owned repository, with A/B isolation,
outage continuity, reconciliation, backup/restore, and visual proof. Do not add
hosted scheduling until this data plane is verified.

## Scope

- [x] Execute and record the secure Phase 6O hosted A/B conformance matrix.
- [x] Map identity/session and all existing account repositories before adding
  an adapter; retire hard-coded hosted-unavailable stubs only from evidence.
- [x] Implement server-derived Supabase session identity without exposing
  secret/service-role credentials or client-selected tenant scope.
- [x] Implement the minimum repository cutover for Watchlist, Attention,
  observations, and Alert Manager with local-first continuity.
- [x] Prove idempotency, optimistic conflicts, export/delete, audit retention,
  A/B isolation, sign-out/new-session restore, outage, recovery, and
  reconciliation.
- [x] Add repository health/SLO truth and generic private-safe failures.
- [x] Capture desktop/390px sign-in, restore, A/B, conflict, outage, recovery,
  and exact research-return evidence.
- [x] Run focused/full tests, performance/privacy/security, release packaging,
  benchmark research, and the final all-28 archive audit.
- [x] Update reports, roadmap, scorecard, visual registry, completed/active
  plans, and the next `/goal` from evidence.

## Boundaries

- No service-role/secret key in browser JavaScript, URL, fixture, screenshot,
  log, report, or release.
- No client-selected user or tenant identity.
- No false hosted success from configuration, migration, or HTTP 200 alone.
- No hosted Cron, email/SMS/push/webhook, billing, broker action, advice, or
  autonomous execution in Phase 6P.
- Local data must remain usable and honestly read-only/queued during an outage;
  recovery must not duplicate or discard audit evidence.

## Acceptance Evidence

Preflight and the reuse/threat map are recorded in
`docs/PHASE_6P_PREFLIGHT_AND_REUSE_MAP.md`. Phase 6N, Phase 6O hosted A/B, and
Phase 6P hosted document A/B evidence pass. The first recovery attempts exposed
exact environment-propagation and credential-shape defects; both were corrected
without weakening server-derived tenancy, public generic errors, or secret
boundaries.

The 2026-07-16 owner run then passed through the normal product session path:
Account A persisted a hosted marker, a fresh process with a distinct empty
SQLite repository restored it exactly, Account B could not read it, and Account
A reconciled cleanup. The bounded journey completed in 17.845 seconds with zero
sign-in retries, diagnostic calls, market-provider calls, or secret/identifier
output. The redacted product and combined summaries passed an independent scan
against 22 configured sensitive values. Hosted scheduling remains deliberately
unverified and disabled; it is Phase 6Q work rather than a Phase 6P claim.

