# Phase 6O Execution Plan

Updated: 2026-07-15
Status: completed for the scoped local-first product contract

## Objective

Turn the existing alert modules and Phase 6N saved-Watchlist observations into
one visible, tenant-safe Watchlist Alert Manager with bounded opt-in local
scheduling and auditable in-app trigger history.

## Completed Scope

- [x] Audited and mapped existing alert, Watchlist, scheduler, persistence,
  API, proxy, UI, and test paths into reuse/retire decisions.
- [x] Defined `watchlist_alert_manager.v1` with separate source/lifecycle
  clocks, rule validation, schedule/worker truth, trigger evidence, and hosted
  readiness.
- [x] Consolidated deterministic rules, due planning, evaluation, dedupe,
  cooldown, persistence, tenant isolation, conflicts, retention, and audit.
- [x] Added bounded opt-in local worker behavior and manual-run fallback with
  zero provider calls from page reads or triage interactions.
- [x] Added account APIs, same-origin proxy, dense Next.js Alert Manager, exact
  evidence drilldown/return, and explicit hosted-unavailable semantics.
- [x] Proved lifecycle, quota, LKG/unavailable, worker outage/restart, conflict,
  Account A/B, empty, mobile, and exact-return states.
- [x] Captured/inspected 18 screenshots and passed the independent visual
  verifier, performance budgets, local actual RLS, remote anonymous denial,
  web gates, and the all-28 archive audit.
- [x] Added a password-safe hosted Phase 6O A/B conformance harness without
  embedding or printing credentials.

## Acceptance Evidence

- due-plan/evaluation/read p95: 9.087/42.921/21.353ms;
- payload/initial HTML: 44,676/44,984 bytes;
- manager provider calls: 0;
- visual: `phase6o.visual.v1`, 18 screenshots, 390px first trigger y=560,
  ProductNav 168px, zero overflow/unexpected errors/provider requests;
- remote migration aligned through `20260715120000`;
- local PostgreSQL Account A/B RLS pass and remote five-table anonymous denial
  pass;
- external audit: 28 archives, 51,305 files, 10,596,233 lines, zero errors.

## Deliberate Unavailable State

The password-authenticated Phase 6O hosted A/B harness has not yet been run.
The product repository remains local-first, and no deployed recurring scheduler
or external delivery channel is claimed. These are Phase 6P/later work, not
silent Phase 6O success.

