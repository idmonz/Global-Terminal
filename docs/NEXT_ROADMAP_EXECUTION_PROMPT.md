/goal Execute Phase 6Q for Global Terminal: deploy and prove one tenant-safe,
free-first hosted observation schedule that reuses the Phase 6N observation and
Phase 6O Alert Manager engines, persists an explainable in-app result through
the verified Phase 6P account repository, and exposes truthful scheduler,
source, freshness, quota, lease, failure, and recovery state. Do not build a
second intelligence engine or claim hosted monitoring from configuration alone.

# Goal

Deliver this complete user journey:

```text
Account A signs in
-> selects one saved Watchlist and one existing alert policy
-> explicitly enables a bounded schedule
-> hosted runtime claims one due window atomically
-> existing provider/quota policy obtains one source-backed observation
-> existing alert evaluator records an explainable in-app result
-> Account A sees last/next run, source, freshness, quota, and caveat
-> an overlapping/retried invocation produces no duplicate run or trigger
-> provider or scheduler failure retains last-known-good with an honest gap
-> Account B sees or mutates none of Account A's schedule/run/trigger state
-> Account A can pause, kill, recover, and safely remove the pilot schedule
```

This is a deployed operations pilot, not a schema-only scheduler dashboard. A
Cron row, HTTP 200, function deployment, fixture, or local loop is insufficient
without an actual hosted invocation and persisted tenant-qualified result.

# Context

Verified continuation baseline as of 2026-07-28. Do not redo the completed
local implementation:

- Phase 6N observation A/B hosted RLS passes all identity, parent-integrity,
  optimistic-version, quota, immutable-audit, deletion, and isolation checks.
- Phase 6O Alert Manager hosted RLS passes rule/evaluation/trigger/worker/audit,
  conflict, recovery, cleanup, and retained-audit checks.
- Phase 6P account continuity passes hosted document A/B RLS and real
  two-repository product recovery. Account A writes one hosted marker, a fresh
  product process with a distinct empty SQLite repository restores it, Account B
  cannot read it, and cleanup reconciles.
- Phase 6P product recovery uses a normal Supabase session and server-derived
  tenant with zero sign-in retries, zero diagnostic calls, zero market-provider
  calls, and no secret/identifier output.
- Hosted network evidence has ten samples: read p50/p95
  188.366/286.160ms; idempotent RPC p50/p95 190.557/221.860ms.
- `phase6p.hosted.handoff.v1` passes while
  `hosted_scheduler_verified=false`. Do not weaken that truth before deployed
  evidence exists.
- `hosted_scheduler_operations.v1`, schema v17, additive Phase 6Q Supabase
  migration, user/service repositories, GitHub Actions Python worker,
  FastAPI/account proxy, fixture, and Alert Manager Hosted schedule tab exist.
- `.github/workflows/quality-gate.yml` now defines secret-free Python and web
  gates for pull requests, `main`, and manual dispatch. Both workflows use six
  reviewed full-SHA action references recorded in `.github/action-pins.json`;
  `.github/dependabot.yml` provides bounded weekly Actions/npm/pip updates.
- `scripts/validate_github_workflows.py` rejects mutable or unknown actions,
  write permissions, `pull_request_target`, missing job timeouts, quality-CI
  secret use, and pin-registry drift. It currently passes with two workflows,
  six action uses, three reviewed actions, zero quality secrets, and four
  allowlisted scheduler secret names.
- The worker restores the Phase 6P account bundle and directly reuses Phase 6N
  observation plus Phase 6O alert evaluation; do not port either engine.
- Local Supabase reset/lint and transactional Account A/B SQL conformance pass
  for safe defaults, RLS, claim/lease/heartbeat, overlap, idempotency, quota,
  source/LKG, failure, kill, recovery, audit, and cleanup.
- Phase 6Q focused tests, compile, fixtures, web test/lint/build/audit,
  24-screenshot `phase6q.visual.v1`, and 200-sample performance evidence pass.
  Initial HTML is 49,002B; scheduler read/compose p95 is 11.412ms; npm audit is
  zero; controlled visual/page paths make zero provider calls.
- The final local continuation suite contains 1,121 tests across 483 files and
  passes in 445.8 seconds. The 24-capture visual set was regenerated and the
  desktop safe default, 390px tall mobile, and Watchlist regression were
  directly inspected again.
- The all-28 audit is unchanged: 51,305 files, 10,596,233 lines, 249,590
  symbols, zero read errors, zero ZIP fingerprint changes, and the existing
  18/6/3/1 license matrix.
- `scripts/run_phase6q_hosted_preflight.ps1 -ProbeLinked -ProbeGitHub` currently
  reports `deployment_ready=false`, but the linked probe is reachable, all
  three migrations are remote-aligned, anonymous clients are denied 5/5, and
  fresh `hosted_rls_verified=true` is independently validated. The owner-run
  Account A/B harness proves zero cross-tenant schedule/run/audit rows, forge
  denial, optimistic conflict, immutable audit, deleted-schedule replacement,
  exact document restoration, unchanged operator controls, and zero provider
  calls. Remaining blockers are no Git commit/private remote/GitHub
  authentication, no deployed default-branch quality or scheduler workflow,
  no protected environment-secret evidence, and no real job history. GitHub
  CLI 2.96.0 is installed; local provider keys exist; local service secret is
  absent; safe scheduler defaults pass.
- The deleted-schedule lifecycle bottleneck is fixed by two additive
  migrations: one non-deleted schedule is allowed per account while a deleted
  schedule no longer blocks replacement. Actual local PostgreSQL proves
  create/delete/recreate/delete.
- `scripts/test-phase6q-hosted-scheduler-rls.ps1` has passed the owner-run gate.
  It used Account A/B user JWTs only, restored the original account document,
  left schedules deleted, changed no operator control, and made zero market
  provider calls. `scripts/verify_phase6q_hosted_rls_summary.py` independently
  accepts the fresh redacted result.
- `scripts/audit_git_publish.py` now scans the complete Git candidate set before
  publication. Its current redacted pass covers 1,834 files, 138,413,688 bytes,
  25 configured values, forbidden paths, and token patterns with zero exact
  secret, forbidden-path, or unreviewed token hits; quality CI runs the same
  gate without receiving `.env`.
- `scripts/verify_phase6q_hosted_evidence.py` now requires all 15 deployment and
  privacy assertions, bounded counts, a real source, job history, and evidence
  freshness. A three-flag JSON can no longer promote hosted verification.
- Read `docs/PHASE_6Q_HOSTED_DEPLOYMENT_HANDOFF.md` and continue from the exact
  blockers. Do not set `hosted_scheduler_verified=true`, archive Phase 6Q, or
  select Phase 6R before the deployed owner handoff passes.
- Require the committed default-branch `Quality gate` to pass before releasing
  the protected `phase6q-pilot` environment to the scheduler workflow. A local
  validator pass is not deployed CI evidence.

# Read First

1. Read the durable goal attachment, root `AGENTS.md`,
   `apps/web/AGENTS.md`, `docs/PLANS.md`, `docs/SECURITY.md`,
   `docs/ROADMAP.md`, parity status, benchmark scorecard, visual registry,
   Phase 6N/6O/6P reports, and `docs/exec-plans/active/PHASE_6Q.md`.
2. Load and follow all six repository skills. Use preflight before edits,
   product-parity for the vertical journey, clean-room for references,
   frontend visual QA for visible changes, release-gate before closure, and
   next-goal-writer only after final evidence.
3. Inspect before creating abstractions:
   - `lib/watchlist_observation_runs.py`,
     `lib/watchlist_alert_manager.py`, `lib/alert_evaluator.py`,
     `lib/alert_deduper.py`, and `lib/research_operations.py`;
   - `scripts/run_watchlist_alert_worker.py`,
     `scripts/run_phase6n_live_smoke.py`, and existing scheduler scripts;
   - account/observation/alert routes in `backend/api/app.py`;
   - Phase 6N, 6O, and 6P migrations, RLS tests, hosted harnesses, and
     account-continuity adapters;
   - `WatchlistAlertManager.tsx`, the Operations/Attention/Watchlist surfaces,
     same-origin proxy, contracts, fixtures, and visual harnesses.
4. Revalidate, do not rewrite,
   `docs/PHASE_6Q_PREFLIGHT_AND_DEPLOYMENT_DECISION.md` and
   `docs/PHASE_6Q_HOSTED_DEPLOYMENT_HANDOFF.md`.
5. Reproduce only the open limitation: browser/page reads make zero provider
   calls and local run-once works, but no deployed recurring invocation exists.

# Required Skills And Prompt Discipline

- Follow `.agents/skills/global-terminal-preflight/SKILL.md`.
- Follow `.agents/skills/global-terminal-product-parity/SKILL.md`.
- Follow `.agents/skills/global-terminal-cleanroom-reference/SKILL.md`.
- Follow `.agents/skills/global-terminal-frontend-visual-qa/SKILL.md`.
- Follow `.agents/skills/global-terminal-release-gate/SKILL.md`.
- Follow `.agents/skills/global-terminal-next-goal-writer/SKILL.md`.
- Recheck the external agent-skills archive and recorded all-28 inventory for
  workflow improvements. Use behavior/instructions only where licensing does
  not permit direct use.

Current official Codex guidance favors a clear Goal, material Context,
Constraints/Boundaries, and Done-when checks, with durable repo rules in
`AGENTS.md` and repeated workflows in skills. Preserve that separation. Do
not replace implementation with a long report.

# Official Hosted References

Verify the current official pages before coding:

- Supabase Cron and job history:
  https://supabase.com/docs/guides/cron
- Scheduled Edge Functions:
  https://supabase.com/docs/guides/functions/schedule-functions
- Edge Function authentication:
  https://supabase.com/docs/guides/functions/auth
- Edge Function limits:
  https://supabase.com/docs/guides/functions/limits
- Edge Function logging:
  https://supabase.com/docs/guides/functions/logging
- Vault:
  https://supabase.com/docs/guides/database/vault

Current official guidance says Cron can run SQL/functions or invoke an Edge
Function, records job-run details, recommends no more than eight concurrent
jobs and ten minutes per job, and recommends Vault for scheduled invocation
secrets. Current Free Edge Function limits include 150 seconds wall time and
two seconds CPU per request. Recheck these facts and design this pilot at one
concurrent job, a much shorter timeout, and a very small symbol/provider budget.

# Implementation Requirements

## 1. Choose One Real Hosted Runner

Select the smallest runner that can execute the existing first-party Python
observation/alert path rather than porting the terminal into a second Deno/TS
engine.

Preferred shape when a public Python backend can be deployed:

```text
Supabase Cron
-> authenticated thin Edge/HTTP dispatcher
-> signed internal FastAPI run-once boundary
-> existing Python observation + alert manager
-> Supabase tenant-qualified rows
```

If the preflight proves a different free-first hosted runner is more viable
(for example, a scheduled CI worker running the existing Python entry point),
choose that one path and record why it is safer and simpler. Do not scaffold
multiple unused clouds. Do not call a localhost process hosted.

The dispatcher may authenticate, validate an invocation envelope, claim work,
and call the existing runner. It must not duplicate provider normalization,
alert evaluation, source scoring, or UI payload composition.

## 2. Scheduler Control Plane

Add the minimum additive migration and reusable Python contract for:

- schedule definition and explicit enabled/paused/killed state;
- normalized timezone and next-due calculation;
- atomic due claim, lease owner, lease expiry, heartbeat, and attempt number;
- deterministic idempotency key per schedule and due window;
- run lifecycle: queued, leased, running, completed, partial, quota-blocked,
  provider-unavailable, cancelled, killed, and failed;
- source/retrieval/observation/evaluation/trigger clocks kept separate;
- provider-call count and quota window;
- last-known-good pointer and bounded retention;
- immutable scheduler audit and operator-safe reason codes.

Use at-least-once invocation plus idempotent effects. Do not claim exactly-once
delivery. Overlap, timeout, retry, and lease recovery must not duplicate an
observation run, alert evaluation, trigger, or audit transition.

Expose one JSON-safe contract such as `hosted_scheduler_operations.v1` through
the reusable `lib/` boundary and FastAPI. Keep React free of Supabase/lease
business logic.

## 3. Tenant And Service Security

- User schedule CRUD derives user/tenant from the verified Phase 6P session.
- Worker claims derive tenant and resource scope from stored due rows, never
  from an arbitrary client body/header/query.
- Ordinary browser CRUD remains user-JWT/RLS scoped.
- Any service/secret key is server/hosted-secret only and absent from browser
  bundles, URLs, fixtures, screenshots, logs, reports, ZIPs, and ordinary user
  routes.
- Do not expose an unauthenticated Edge Function or worker endpoint. If platform
  auth cannot protect the invocation, add a narrow replay-resistant signed
  envelope and document the threat review before deployment.
- Add composite parent/tenant foreign keys, RLS, least privilege, conflict
  versions, immutable audit, and cross-tenant negative tests.
- Keep QA diagnostics loopback/explicit and public failures generic.

## 4. Bounded Provider And Quota Behavior

Pilot only one small saved Watchlist and existing provider capabilities. Enforce
per-run symbol/capability/call/time limits before deployment. Reuse Phase 6N's
quota planner and stale/LKG semantics.

- Page load, triage, schedule editing, and history reads make zero provider
  calls.
- Only a successfully leased due job may spend provider quota.
- A replayed or overlapping invocation spends no additional quota.
- A provider 429, timeout, forbidden response, missing key, or malformed payload
  becomes explicit partial/unavailable truth and never a fabricated trigger.
- A source-backed result carries provider, source URL, retrieved/fetched/
  observed timestamps, freshness, status, confidence, caveat, and data gap.
- Compare the live smoke's timing/value/status with an official or primary
  provider surface via web research; record delay and mismatch caveats rather
  than assuming two providers should be identical.

## 5. Kill Switch, Recovery, And Operations

The hosted worker is disabled by default. Enabling requires explicit Account A
consent plus an operator deployment flag. Provide:

- global emergency kill switch and tenant schedule pause;
- bounded timeout, no blind retry loop, and expired-lease recovery;
- no-due, quota-blocked, provider-offline, partial-LKG, killed, cancelled, and
  recovered states;
- structured private-safe logs and stable correlation IDs;
- invocation, claim, duration, provider-call, result, duplicate-suppression,
  error, and recovery metrics;
- a safe disable/unschedule/cleanup command and rollback notes.

Do not log headers, cookies, tokens, emails, UUIDs, provider keys, raw provider
bodies, private notes, or payload rows. Hosted platform logs and
`cron.job_run_details` are supporting evidence, not the only product ledger.

## 6. Commercial Product Surface

Extend the existing Alert Manager or Operations surface; do not create an
architecture dashboard as the primary experience. A signed-in user must see:

- schedule state, timezone, next due, last attempted/completed run;
- live/cache/stale/unavailable source truth and last-known-good age;
- provider budget used/remaining and why a capability was skipped;
- lease/running state in plain language, not raw infrastructure fields;
- last evaluation/trigger with exact evidence drilldown and return;
- pause/resume/kill/retry controls with confirmation and visible live status;
- explicit `hosted-unverified` or `disabled` state until owner evidence passes.

Use compact terminal density, stable responsive tracks, Lucide icons/tooltips,
keyboard operation, visible focus, live regions, and no crushed ProductNav or
Research rail. No UUIDs, tokens, local paths, SQL errors, raw Cron rows, or
contract debug dumps in the main UI.

## 7. Hosted Conformance Handoff

Continue the existing password/token-safe owner handoff. Do not create a second
harness. First run `scripts/test-phase6q-hosted-scheduler-rls.ps1`, retain its
redacted pass, then extend the same evidence chain into the worker pilot. It
must:

- run a no-secret preflight before prompting or mutating hosted state;
- verify linked migration/function/job versions and exact runtime configuration;
- request any necessary Account A/B password only as `SecureString`;
- reuse the bounded temporary Account A schedule lifecycle proven by the RLS
  harness, then create one explicit pilot due window;
- observe one actual hosted claim/run/result and its job/function history;
- prove Account B read/write isolation;
- invoke an overlap/retry and prove no duplicate/provider overspend;
- exercise kill switch and one controlled provider/scheduler failure;
- recover, clean up temporary rows/job, and preserve required immutable audit;
- emit only redacted versioned JSON summaries;
- report `hosted_scheduler_verified=true` only after every assertion passes.

If the deployed invocation cannot be exercised, keep
`hosted_scheduler_verified=false`, keep the schedule disabled, document the
exact external blocker, and do not close Phase 6Q.

# Quantitative Acceptance

- one concurrent hosted pilot job;
- configured function/worker deadline comfortably below the current platform
  limit and explicitly enforced;
- maximum symbols, provider capabilities, calls, retries, and retained rows are
  finite and tested;
- zero provider calls on page/read/edit/triage paths;
- zero additional provider calls for overlap/idempotent replay;
- zero duplicate run/evaluation/trigger/audit effect for one due window;
- zero cross-tenant rows visible or mutable by Account B;
- scheduler read/compose local p95 below 75ms, hosted/network latency measured
  separately with sample count and p50/p95;
- initial affected-route HTML below decimal 100KB unless an evidence-backed
  exception is approved;
- no secret/token/private identifier/path/note/provider body in public payload,
  fixture, screenshot, log, report, or release archive.

# Required Tests And QA

Add focused pure-Python, API, migration/RLS, dispatcher/worker, frontend,
performance, hosted-harness, visual-harness, privacy, and release tests. Prove
due calculation, timezone/DST boundary, lease contention/expiry, idempotency,
quota exhaustion, provider failure, kill switch, optimistic conflict, retained
audit, A/B isolation, and cleanup.

Run at minimum:

```powershell
python -m pytest -q -x
python -m pytest tests/test_phase6q_* -q
python -m pytest -q
python -m py_compile <changed Python files>
python scripts/export_api_fixtures.py
npm.cmd --prefix apps/web test
npm.cmd --prefix apps/web run lint
npm.cmd --prefix apps/web run build
npm.cmd --prefix apps/web audit --audit-level=high
```

Run the repository smoke/harness validators, the actual hosted handoff, the
all-28 external audit, focused release-hygiene tests, fresh release build, and
release security inspection. Record exact counts, versions, timings, hashes,
skips, warnings, and unavailable states.

# Visual QA

Create `phase6q.visual.v1` capture and an independent verifier. Capture and
personally inspect desktop plus 390x844:

- hosted-unverified/disabled default;
- explicit enable and next-due state;
- leased/running progress;
- completed source-backed result and exact evidence return;
- no-due and idempotent replay;
- quota-blocked and provider-offline/LKG;
- kill switch, expired lease, recovery, and cleanup;
- Account A/B isolation and session expiry;
- regressions for Alert Manager, Operations, Attention, Watchlist, Analyst, and
  map/news return.

Assert nonblank primary charts/maps where present, zero horizontal overflow,
overlap, clipped text, crushed navigation, duplicate IDs, unlabeled controls,
unexpected browser errors, and hidden provider requests. Verify visible focus,
live status, route return state, and screenshot bytes. Register only evidence
produced by a passing real capture harness.

# Clean-Room And Benchmark Boundary

- Re-run the recorded external audit over all 28 archives and investigate any
  fingerprint delta. Mechanical indexing is not copy permission.
- WorldMonitor/OpenBB/OpenStock and other restrictive archives remain
  behavior-only; NASA/missing-license/unclear-license paths remain blocked or
  clean-room.
- Permissive code still requires exact-path license/notice review before direct
  adaptation. Prefer first-party implementation.
- Compare current official TradingView watchlist-alert continuity, OpenBB
  source-aware persistent operations, and Supabase scheduling/observability
  behavior. Recreate useful behavior without copying visual assets, brands,
  datasets, or source.

# Boundaries

- no email, SMS, push, browser notification, webhook, external delivery, billing,
  entitlement, broker connection, order routing, trade recommendation, trade
  approval, paper/live trading, or autonomous action;
- no unbounded background refresh or provider fan-out;
- no service-role/secret credential in browser or ordinary account CRUD;
- no client-selected tenant/user/resource scope;
- no destructive remote reset; use additive migration, bounded temporary rows,
  backup, rollback, and explicit cleanup;
- no fixture/static/local process promoted to hosted/live;
- keep Streamlit as lab, `lib/` reusable, FastAPI as API boundary, Next.js as
  commercial surface, and exactly one active execution plan;
- keep the durable parity goal active after Phase 6Q unless every master
  benchmark category actually reaches score 5 with evidence.

# Done When

Phase 6Q is complete only when:

1. One real hosted schedule is deployed, invoked, observed, and safely disabled
   or left explicitly enabled by owner choice.
2. It reuses the existing observation/alert engine and persists one
   tenant-qualified source-backed result.
3. Retry/overlap, quota, failure, kill, lease recovery, A/B isolation, and
   cleanup evidence pass.
4. The product exposes useful scheduler/source/quota truth without becoming an
   infrastructure dashboard.
5. Hosted evidence is redacted, fresh, versioned, and independently validated.
6. Focused/full, web, security, performance, visual, external, and release gates
   pass.
7. Reports, roadmap, parity status, scorecard, visual registry, completed/active
   plan, release report, and next evidence-selected `/goal` are updated.

# Final Response

Report the deployed runner path, actual hosted job/function versions, migration
and RLS truth, Account A/B evidence, schedule/run/provider/trigger counts,
source/freshness/quota truth, overlap/failure/recovery results, visual evidence,
tests, release archive/hash, remaining unavailable capabilities, owner actions,
and next phase. Do not call the product benchmark-grade, always-on, or
production-ready beyond the exact evidence.
