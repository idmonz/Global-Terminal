# Phase 6Q Preflight And Deployment Decision

Updated: 2026-07-27

## Phase Contract

Phase 6Q promotes one saved-Watchlist observation and in-app alert journey from
an explicitly started local process to one bounded hosted schedule. The phase
uses at-least-once delivery with idempotent effects. It does not claim
exactly-once execution, external notification delivery, recommendation,
broker action, or general production readiness.

The completion boundary remains strict: configuration, a migration, a CI
workflow file, or a successful local run cannot set
`hosted_scheduler_verified=true`. One real hosted invocation, persisted
tenant-qualified source-backed result, replay suppression, Account A/B
isolation, failure/recovery, kill, cleanup, and redacted evidence must pass.

## Fresh Baseline

The 2026-07-27 preflight found and repaired two time-sensitive baseline defects
before Phase 6Q product work:

1. `tests/test_phase6o_alert_api.py` used a fixed expiration timestamp that
   became historical after 2026-07-22. The API correctly rejected it. The API
   integration helper now creates a seven-day future expiration while the pure
   validator tests keep an injected deterministic clock.
2. New npm advisories made the prior Next.js 16.2.9 dependency set fail the
   high-severity audit. The web app now uses Next.js and eslint-config-next
   16.2.12, patched PostCSS and Sharp dependencies, and a reproducible
   minimatch compatibility patch for the fixed brace-expansion API.

Accepted pre-edit baseline after those corrections:

- full Python: 1,088 tests passed; one existing Starlette/httpx deprecation and
  two existing cointegration collinearity warnings;
- compileall, six-skill/one-active-plan harness, and smoke imports: passed;
- deterministic export: 34 fixtures;
- web fixture/runtime test, lint, and Next.js 16.2.12 production build: passed;
- npm high-severity audit: zero vulnerabilities;
- release: 1,801 selected files plus manifest, 1,802 ZIP entries.

Linked Supabase inspection reached the project but the migration-list request
returned a transient login-role connection timeout. `supabase functions list`
returned no deployed functions. No Phase 6Q migration or hosted worker exists
at this baseline.

Post-implementation update: CLI connectivity recovered and the linked project
now aligns through `20260727143000`, `20260727190000`, and `20260727191500`.
Anonymous access is denied 5/5. This supersedes the transient baseline timeout
but does not prove Account A/B user-session isolation or worker execution.

## Reuse And Retirement Map

| Existing boundary | Phase 6Q decision |
|---|---|
| `ObservationRunCoordinator` and `SourceBackedObservationAdapter` | Reuse unchanged as the only provider-normalization and observation engine. Run inline inside the bounded hosted worker. |
| `WatchlistAlertManagerStore.evaluate_due` | Reuse as the only alert evaluator/deduper. It consumes the newly committed stored observation and makes zero provider calls. |
| Phase 6P account document | Restore into an isolated temporary SQLite repository, execute the existing engines, then atomically persist the bounded updated document through a lease-qualified service RPC. |
| Phase 6N quota planner and LKG rows | Reuse. The hosted pilot narrows the limit to one Watchlist, at most five symbols, and at most sixteen provider operations; the owner pilot defaults lower. |
| Local Phase 6O worker loop | Keep for explicit local QA only. It is not a hosted runner and is not started by page reads. |
| Supabase Cron plus Edge Function | Do not implement in this phase because no public Python backend exists. Porting provider and alert logic to Deno would create a second intelligence engine. |
| Anonymous HTTP dispatcher | Retire as an option. The selected runner calls service-only Supabase RPCs and has no public worker endpoint. |

## Selected Runner

Select one **private GitHub Actions scheduled Python worker**.

```text
GitHub Actions schedule / explicit dispatch
-> secret-scoped Python worker
-> service-only atomic Supabase due claim
-> Phase 6P account document restored to an isolated temporary SQLite file
-> existing Phase 6N observation engine
-> existing Phase 6O alert evaluator and deduper
-> lease-qualified atomic account-document and scheduler-result commit
-> temporary local repository destroyed
```

Reasons:

- it executes the first-party Python path without a second Deno/SQL evaluator;
- it needs no anonymous inbound endpoint;
- job concurrency, timeout, history, manual dispatch, and secret boundaries are
  native;
- an hourly pilot stays within a bounded free-first posture more plausibly than
  a five- or fifteen-minute private-repository schedule;
- minute 17 avoids the top-of-hour period that GitHub documents as more prone
  to delayed scheduled runs.

The workflow is one concurrent job, read-only `GITHUB_TOKEN`, a short timeout,
and disabled unless an explicit repository variable and database control gate
are both enabled. GitHub scheduling can be delayed or dropped and is not an
SLO-grade scheduler. Product copy must expose that caveat.

## Current Deployment Blocker

The local repository has no commit, no Git remote, no GitHub CLI, and no
deployed worker repository. The configured local `.env` has a Supabase URL and
publishable key but no `SUPABASE_SECRET_KEY` or legacy service-role key. These
are correct pre-deployment conditions: no privileged credential is inferred or
created from a publishable key.

Implementation, local/PostgreSQL conformance, migration deployment, and a
password-safe owner handoff can proceed. Actual hosted invocation requires the
owner to create or approve a private GitHub repository and add repository
secrets after the release boundary is inspected. Until then the schedule and
operator gates remain disabled and `hosted_scheduler_verified=false`.

## Cost And Quota Boundary

- workflow cadence: hourly pilot at minute 17, never faster than five minutes;
- workflow concurrency: one, with overlap cancellation disabled so the
  database lease remains authoritative;
- timeout: four workflow minutes and a materially shorter worker deadline;
- pilot scope: one account, one saved Watchlist, one existing alert policy;
- hard bounds: maximum five symbols, sixteen provider operations, one retry,
  and finite result/audit retention;
- page reads, editing, triage, and history: zero provider calls;
- an overlap, replay, disabled gate, no-due window, or unclaimed lease: zero
  provider calls;
- provider keys remain optional. Missing key, 429, timeout, forbidden, and
  malformed data produce explicit partial/unavailable outcomes.

GitHub documents 2,000 included private-repository Actions minutes for the
Free plan at the current reference date, but billing and plan limits can change.
The product does not treat that allowance as an entitlement or SLO.

## Threat Model

- The worker credential is a repository/environment secret and never enters a
  browser bundle, fixture, URL, screenshot, report, archive, or ordinary user
  route.
- User CRUD uses the Phase 6P user session and RLS. Worker claim/commit RPCs are
  service-only and derive tenant, owner, Watchlist, and account document from
  the claimed schedule row.
- A raw client tenant, user, lease owner, due window, run status, or account
  document version is never authoritative.
- Claim uses row locking and an expiring lease. Commit requires the matching
  lease secret and account-document version. A replay returns the existing
  run and spends no provider quota.
- The worker prints only stable reason codes, counts, durations, and hashed
  correlations. It never prints tokens, headers, cookies, emails, UUIDs,
  provider keys, rows, private notes, or raw provider bodies.
- Global operator kill, tenant pause/kill, deadline, call cap, and attempt cap
  are checked before provider work and again before commit.
- Account-document conflict does not overwrite newer user state. It records an
  honest partial/failure outcome and preserves the prior last-known-good state.

## Rollback And Cleanup

1. Set the repository scheduler variable false.
2. Set the database operator kill switch true.
3. Pause or kill the tenant pilot schedule.
4. Let active leases expire or finish them with a stable cancelled/killed code.
5. Remove the GitHub schedule while retaining the manually dispatchable
   credential-free preflight if desired.
6. Delete bounded schedule/run rows only through the owner handoff; retain the
   immutable audit required by the migration.
7. Rotate the worker secret after the pilot or any suspected exposure.

The migration is additive. Rollback disables work instead of destructively
reverting prior Phase 6N-6P data.

## Owner Actions Reserved For Deployment

After local, migration, security, and release gates pass:

1. approve a private GitHub repository containing only the inspected source
   release boundary, not `.env`, external archives, review evidence, or private
   databases;
2. add `SUPABASE_URL` and a dedicated Supabase secret/service credential as
   repository or protected-environment secrets;
3. add only the provider keys needed by the one-symbol pilot;
4. deploy the additive migration, keep both global and repository gates off,
   and run the no-secret preflight;
5. explicitly enable the temporary Account A pilot, run the hosted handoff,
   inspect redacted evidence, then disable or retain the schedule by explicit
   owner choice.

No owner action is requested before the implementation and local gates are
complete.

## Official Evidence

- Supabase Cron and job history: <https://supabase.com/docs/guides/cron>
- Scheduled Edge Functions: <https://supabase.com/docs/guides/functions/schedule-functions>
- Edge Function authentication: <https://supabase.com/docs/guides/functions/auth>
- Edge Function limits: <https://supabase.com/docs/guides/functions/limits>
- Supabase Vault: <https://supabase.com/docs/guides/database/vault>
- GitHub scheduled workflows: <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule>
- GitHub Actions billing: <https://docs.github.com/en/actions/concepts/billing-and-usage>
- GitHub Actions secure use: <https://docs.github.com/en/actions/reference/security/secure-use>
