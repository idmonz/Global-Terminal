# Phase 6O Watchlist Alert Manager Implementation Report

Updated: 2026-07-15

## Outcome

Phase 6O turns the previous preview-only alert fragments into one visible,
tenant-qualified `watchlist_alert_manager.v1` product journey:

```text
saved Watchlist -> create a deterministic rule -> plan due work
-> evaluate a stored Phase 6N observation -> dedupe/cooldown
-> persist an in-app trigger -> inspect exact evidence -> return
```

The manager is local-first. Reading, filtering, reviewing, exporting, and
navigating the manager make zero market-provider calls. Manual evaluation reads
validated stored observations. The optional worker is disabled unless explicitly
enabled and page views never start it.

## Product Surface

- `lib/watchlist_alert_manager.py` owns validation, tenant-scoped persistence,
  due planning, deterministic evaluation, dedupe, cooldown, retention, audit,
  worker truth, fixtures, and the JSON-safe contract.
- `lib/api_contracts.py` and `backend/api/app.py` expose account-scoped manager,
  rule, evaluation, trigger, audit, export, and manual worker endpoints.
- `apps/web/src/app/api/account/[...path]/route.ts` keeps these calls same-origin,
  route-bounded, CSRF-protected, and server-session scoped.
- `WatchlistAlertManager.tsx` provides compact Rules, History, and Runs views,
  lifecycle controls, source clocks, caveats/gaps, and exact Analyst, News,
  Brief, and Map evidence links.
- Watchlist and Attention navigation now reach the Alert Manager without
  exposing contract diagnostics as the primary experience.

## Rule And Worker Truth

Supported rule types are `price_above`, `price_below`,
`absolute_percent_move`, `material_saved_change`, and `source_degradation`.
Every rule requires an exact asset, metric/operator, applicable threshold and
unit, frequency, session policy, cooldown, expiration, severity, source state,
caveat, and missing-data outcome.

The worker is bounded by the Phase 6N five-symbol, 16-operation, concurrency-two
caps. Its safe defaults are disabled, observation calls disabled, and a
300-second interval. Manual run remains available. No email, SMS, push,
webhook, browser notification, broker action, recommendation, or autonomous
execution exists in this phase.

## Persistence And Hosted Boundary

Local persistence enforces stable tenant-qualified identifiers, fingerprints,
idempotency, optimistic versions, bounded retention, trigger dedupe, and
append-only lifecycle audit evidence.

Migration `20260715120000_phase6o_watchlist_alert_manager.sql` is present on
both local and linked remote histories. It adds RLS-protected rules,
evaluations, triggers, audit, and worker-state tables plus composite foreign
keys back to Watchlist and Phase 6N observation parents.

Verified now:

- local PostgreSQL Account A/B functional RLS matrix passes;
- the linked project denies anonymous reads on all five tables with HTTP 401;
- remote migration history is aligned;
- pre/post deployment schema evidence and a private pre-deployment data backup
  exist outside the release boundary;
- `scripts/test-phase6o-alert-rls.ps1` provides a password-prompted, token-safe
  hosted A/B test for isolation, cross-parent integrity, optimistic conflict,
  worker recovery state, audit immutability, cleanup, and retained audit.

Not verified yet:

- the Phase 6O password-authenticated hosted script has not been executed;
- the commercial runtime still uses its local repository rather than a
  Supabase-backed account repository;
- no deployed recurring scheduler, scheduler outage drill, backup restore, or
  production SLO is claimed.

The product therefore reports hosted alert scheduling as unavailable. A
migration or configured key is not treated as live monitoring.

## Quantitative Result

`review_workspace/phase6o_performance.json` passes:

- five symbols, 30 samples;
- due-plan p95 9.087ms;
- evaluation p95 42.921ms;
- manager read p95 21.353ms;
- payload 44,676 bytes;
- provider calls during manager operations 0.

These timings exclude upstream provider and hosted network latency.

## Remaining Bottleneck

The Alert Manager is useful and visually proven, but it is not an always-on
commercial monitoring service. The next bottleneck is a real Supabase account
session and repository cutover with password-authenticated A/B, outage,
recovery, export/delete, and backup/restore evidence. Hosted scheduling should
follow only after that data plane is proven.

