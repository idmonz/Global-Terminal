# Phase 6Q Implementation And Gap Report

Updated: 2026-07-27

## Verdict

Phase 6Q has a complete local product/control-plane implementation and a tested
deployment package, but it is not complete as a hosted phase. The product must
continue to display `hosted-unverified` because the selected scheduled workflow
is not on a committed default branch, password-authenticated Phase 6Q A/B
conformance has not run, and no real hosted job/result/history exists. The
linked schema and anonymous-denial gates now pass.

## Implemented Product Slice

- `hosted_scheduler_operations.v1` JSON-safe schedule, run, source, quota, LKG,
  audit, readiness, and safe-control contract;
- schema v17 local persistence plus additive Supabase schedule/control/run/audit
  migration, two deleted-schedule lifecycle hardening migrations, and
  user/service RPC boundaries;
- atomic due claim, one concurrency, hashed lease proof, heartbeat, expiry,
  bounded attempts, deterministic due-window idempotency, optimistic schedule
  versions, and at-least-once/idempotent-effects semantics;
- private GitHub Actions Python worker with a four-minute timeout that restores
  the Phase 6P account bundle and directly invokes Phase 6N observations plus
  Phase 6O alert evaluation;
- secret-free/minimum-permission quality workflow for Python, web, fixture,
  release, and dependency gates; six reviewed full-SHA action uses, a
  first-party pin registry, fail-closed validator, and bounded Dependabot
  policy;
- FastAPI account routes and same-origin Next proxy with server-derived tenant
  scope, CSRF on user controls, bounded payloads, and no browser service key;
- compact Alert Manager Hosted schedule tab with explicit consent, next/last
  clocks, source/freshness, quota, LKG, pause/resume/retry/kill/recover/delete,
  and honest disabled/unverified states;
- deterministic fixture, local actual-Postgres conformance, performance, visual,
  preflight, evidence-template, and independent hosted-evidence verifier.

## Security And Truth Boundary

The database defaults remain operator disabled, globally killed, and unverified.
New Supabase `sb_secret_*` keys are sent only as `apikey`; they are never copied
into `Authorization: Bearer`, browser variables, fixtures, URLs, screenshots,
reports, or release archives. Legacy service-role JWT support remains compatible.

The hosted verifier now requires 15 assertions plus bounded counts, a fresh
source-backed result, an explainable trigger, job history, safe final schedule
state, and privacy scans. A JSON containing only `passed=true` and
`hosted_scheduler_verified=true` fails.

## Measured Evidence

- local Supabase DB lint: zero findings;
- transactional Account A/B SQL conformance: pass for RLS, safe default, claim,
  lease, overlap, replay, account-document idempotency, source/LKG, provider
  failure, kill, recovery, immutable audit, and cleanup;
- scheduler read/compose: 200 samples, p50 6.894ms, p95 11.412ms, 75ms limit;
- safe-default claim p95: 0.010ms; provider calls: zero;
- Alert Manager initial HTML: 49,002 bytes under the 100KB budget;
- `phase6q.visual.v1`: 24 screenshots, zero overflow, duplicate IDs, unlabeled
  controls, unexpected errors, or provider reads;
- all 28 external archive hashes unchanged; 51,305 files, 10,596,233 lines,
  249,590 symbols, zero read errors.
- full local regression: 1,121 tests across 483 files passed in 445.8 seconds;
  web test/lint/build and high-severity audit pass with zero vulnerabilities.

## Benchmark Comparison

TradingView documents that alerts continue server-side after the client closes.
Global Terminal now has the necessary server-side control and product semantics,
but has not yet demonstrated that continuity in a deployed runner, so parity is
not claimed:
https://www.tradingview.com/support/solutions/43000548327-will-alerts-work-if-tradingview-is-not-open-on-the-computer/

OpenBB Workspace treats source metadata, parameters, visual type, and linked
widget state as first-class. Global Terminal's source/clock/quota contract and
linked research routes move in that direction, but it does not yet offer a
general user-composable widget canvas:
https://docs.openbb.co/workspace/analysts/widgets/overview

GitHub scheduled workflows may be delayed or dropped under load and only run
from the default branch. The worker therefore promises at-least-once invocation
with idempotent effects, never exactly-once or precise wall-clock delivery:
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

## Open Blockers

1. The remote Phase 6Q schema and anonymous-denial gates pass, but the
   password-authenticated Account A/B scheduler RLS handoff has not yet run.
2. The repository has no commit, private origin, or GitHub CLI authentication.
3. Neither the quality workflow nor scheduler workflow is deployed on a default
   branch; local workflow validation is not GitHub execution evidence.
4. The `phase6q-pilot` GitHub environment and four secret names are unverified.
5. No actual job history, source-backed hosted result, overlap replay, controlled
   failure, kill/recovery, or deployed cleanup evidence exists.

Follow `docs/PHASE_6Q_HOSTED_DEPLOYMENT_HANDOFF.md`. Do not select Phase 6R until
all five blockers close and the independent hosted verifier passes.
