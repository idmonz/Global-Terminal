# Phase 6Q Execution Plan

Updated: 2026-07-28
Status: implementation in progress; hosted deployment remains disabled

## Objective

Promote exactly one saved-Watchlist observation and in-app alert journey from
the bounded local worker into a tenant-safe hosted schedule with leases,
idempotency, quota caps, kill switch, failure recovery, and operator-visible
truth.

## Planned Scope

- [x] Run repository, hosted-runtime, provider-quota, security, and release
  preflight; choose one deployable free-first runner path.
- [x] Reuse Phase 6N observation and Phase 6O alert contracts instead of
  creating a second evaluation engine.
- [x] Add additive hosted schedule/lease/run/audit persistence with strict
  Account A/B isolation and server-derived tenant scope.
- [x] Prove the local and actual-Postgres at-least-once contract with idempotent run/trigger outcomes,
  overlap protection, bounded retries, and kill-switch behavior.
- [ ] Exercise one real source-backed scheduled run and one no-op/retry window
  through the deployed runner without exceeding provider quotas.
- [x] Expose compact schedule health, next/last run, quota, source/freshness,
  LKG, and failure truth in the existing Alert/Operations product surface.
- [ ] Prove deployed job history, Account B isolation, provider outage,
  scheduler outage/recovery, and zero page-read provider calls.
- [x] Capture and inspect desktop/390px visuals; run focused/full, security,
  performance, external-audit, web, and release gates.
- [x] Update reports, roadmap, scorecard, visual registry, completed/active
  plans, and the next evidence-selected `/goal`.

## Hard Boundaries

- No anonymous scheduler endpoint, browser service-role key, client-selected
  tenant, unbounded provider fan-out, or false exactly-once claim.
- No email, SMS, push, webhook, broker action, billing, recommendation, trade
  execution, or autonomous financial action.
- Scheduler and provider work are disabled by default until the owner-run
  deployment handoff passes.
- A configured Cron job, HTTP 200, or fixture is not hosted monitoring proof.

## Completion Evidence

The phase closes only after an actual hosted invocation creates one
tenant-qualified, source-backed observation and any explainable in-app trigger;
a retry/overlap creates no duplicate; Account B remains isolated; kill switch
and provider failure preserve last-known-good truth; the UI exposes the exact
run/source/quota clocks; all visual/test/release gates pass; and the deployed
schedule can be safely disabled and cleaned up.

## Progress And Decisions

- 2026-07-27: fresh preflight repaired a date-sensitive Phase 6O API test and
  upgraded the web security baseline to Next.js 16.2.12 with zero npm audit
  vulnerabilities. Full 1,088-test Python, web, harness, smoke, fixture, build,
  and release baselines pass.
- 2026-07-27: selected one private GitHub Actions scheduled Python worker. It
  preserves the Phase 6N/6O Python engines and avoids an anonymous dispatcher or
  duplicate Deno evaluator.
- 2026-07-27: the linked Supabase project is reachable and remote-aligned
  through the base scheduler migration plus two deleted-schedule recreation
  hardening migrations. Anonymous access to four scheduler tables and the user
  RPC is denied 5/5 with zero provider calls. This proves schema and anonymous
  denial. Password-authenticated Phase 6Q Account A/B RLS now also passes with
  zero cross-tenant rows, exact document restoration, and zero provider calls;
  worker execution remains unverified.
- Detailed reuse, threat, quota, rollback, cost, and owner-action decisions are
  recorded in `docs/PHASE_6Q_PREFLIGHT_AND_DEPLOYMENT_DECISION.md`.
- 2026-07-27: implemented `hosted_scheduler_operations.v1`, the additive
  Supabase schedule/run/audit control plane, the private GitHub Actions Python
  worker, service/user repositories, FastAPI/Next account routes, and the
  compact Hosted schedule tab. The worker restores the Phase 6P account bundle
  and directly reuses the Phase 6N/6O Python engines.
- 2026-07-27: local Supabase migration reset/lint and transactional Account A/B
  conformance pass with overlap suppression, idempotent replay, quota, LKG,
  provider failure, global kill, lease recovery, audit, and cleanup. This is
  local database evidence, not deployed hosted evidence.
- 2026-07-27: `phase6q.visual.v1` independently verifies 24 screenshots,
  49,002-byte initial HTML, 168px desktop navigation, 390px mobile no-overflow,
  visible focus/live status, zero hidden provider calls, and all controlled
  failure states. The completed visual is explicitly a controlled source
  fixture and does not promote hosted verification.
- 2026-07-27: the redacted deployment preflight now reports the linked probe
  reachable and `remote_migration_applied=true`. It remains blocked by missing
  Git commit/remote/GitHub authentication, deployed workflows, protected
  environment-secret evidence, and real job history. The
  operator gate stays off, global kill stays armed, and
  `hosted_scheduler_verified=false`.
- 2026-07-27: a PostgreSQL-truncated legacy unique-constraint name exposed a
  commercial lifecycle defect: a soft-deleted schedule blocked every future
  schedule. A catalog-resolved additive migration now enforces one non-deleted
  schedule while allowing a bounded replacement. Local actual-Postgres
  conformance proves create/delete/recreate/delete, and a secret-safe hosted
  Account A/B harness is ready for owner password entry.
- 2026-07-27: final local gates pass: 1,121 Python tests, web test/lint/build,
  zero high-severity npm audit findings, 24 inspected screenshots, actual local
  PostgreSQL conformance, 200-sample performance, and both full external audits.
  Release packaging was repaired to include first-party GitHub configuration;
  rebuilt archives have zero configured-secret hits, zero forbidden entries,
  and no missing Phase 6Q deployment files.
- 2026-07-28: the owner-run Account A/B hosted scheduler RLS harness passes
  against the linked Supabase project. It proves distinct identities/tenants,
  zero cross-tenant schedule/run/audit visibility, forge denial, optimistic
  conflict, immutable audit, deleted-schedule replacement, exact account
  document restoration, unchanged operator controls, and zero provider calls.
  `scripts/verify_phase6q_hosted_rls_summary.py` independently validates the
  fresh redacted evidence and refuses to promote hosted worker verification.
- 2026-07-28: GitHub CLI 2.96.0 is installed but deliberately unauthenticated.
  A new Git publish audit checks all 1,834 candidate files (138,413,688 bytes),
  25 configured values, forbidden paths, and token patterns; it passes with
  zero exact-value, forbidden-path, or unreviewed token hits and now runs in
  secret-free quality CI.

## CI And Supply-Chain Hardening Continuation

The default-branch invocation remains an external blocker, but the repository
can still remove deployment risk before publication.

- [x] Pin every first-party GitHub workflow action to an independently recorded
  full commit SHA and retain the reviewed release tag as metadata.
- [x] Add a minimum-permission, secret-free quality workflow for Python,
  Next.js, fixtures, release hygiene, and dependency audit gates.
- [x] Add bounded Dependabot policies for GitHub Actions, npm, and pip.
- [x] Add an independent validator that rejects mutable action tags, unknown
  actions, write permissions, unbounded jobs, secret use in CI, and missing
  release/security gates.
- [x] Extend the read-only deployment preflight and release tests so the quality
  workflow, pin registry, and dependency policy cannot silently disappear.
- [x] Run focused/full workflow, Python, web, release, and security gates. Keep
  hosted verification false until the actual deployed pilot passes.

Acceptance requires zero provider calls and zero private secret access from the
quality workflow. Passing local validation proves repository readiness only; it
does not prove a GitHub workflow was deployed or executed.

## Hosted Handoff Continuation

- [x] Apply and verify all three linked Phase 6Q migrations.
- [x] Prove anonymous denial on four scheduler tables and the user RPC (5/5).
- [x] Repair deleted-schedule replacement and prove it in actual local
  PostgreSQL.
- [x] Add a user-JWT-only, cleanup-safe Account A/B hosted RLS harness.
- [x] Run that harness with Account A/B SecureString passwords and retain its
  redacted pass summary.
- [ ] Create the reviewed private Git commit/origin and deploy a passing
  default-branch quality workflow.
- [ ] Configure the protected `phase6q-pilot` environment, run the bounded
  worker pilot/replay/failure/recovery/cleanup sequence, and pass the hosted
  evidence verifier.

The local hardening continuation passes its Python, web test/lint/build/audit,
actual-Postgres, and fresh 24-capture visual regression gates. The validator
accepts six pinned action uses across two workflows, three reviewed action
identities, zero quality-gate secret references, and the four allowlisted
scheduler secret names. Full archive and license audits remain unchanged. The
remote schema and anonymous-denial gates now pass. Git commit, remote, GitHub
authentication, deployed quality/scheduler workflows, protected environment
secrets, and hosted job evidence remain absent. Password-authenticated Phase 6Q
A/B RLS evidence now passes independently; GitHub CLI is installed but not yet
authenticated.
