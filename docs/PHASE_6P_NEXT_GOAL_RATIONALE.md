# Phase 6P Next Goal Rationale

Updated: 2026-07-16

## Decision

Select **Phase 6Q: Hosted Observation Scheduler And Alert Operations Pilot**.

Phase 6P closes the account data-plane prerequisite. Real Supabase Account A/B
document isolation, optimistic conflict behavior, immutable audit,
server-derived tenancy, fresh-process restore into a distinct local repository,
and cleanup reconciliation now pass. The largest remaining commercial trust gap
is that observation and alert work still depends on an explicitly started local
process. A user cannot yet rely on one saved Watchlist being checked while the
browser and owner machine are offline.

## Evidence

- Phase 6N observation and Phase 6O Alert Manager hosted A/B RLS matrices pass.
- Phase 6P account document A/B and two-repository product recovery pass.
- The final product recovery uses a normal Supabase product session, performs
  no diagnostic retry, makes zero market-provider calls, and leaks none of 22
  checked configured sensitive values.
- Hosted read p50/p95 is 188.366/286.160ms and idempotent RPC p50/p95 is
  190.557/221.860ms over ten network-inclusive samples.
- `hosted_scheduler_verified=false` remains explicit in the accepted handoff.
- TradingView-style always-on watchlist alerts and OpenBB-style persistent
  source-aware operations remain stronger than the current local worker.

## Selected Vertical

```text
Account A enables one bounded saved-Watchlist schedule
-> hosted runtime claims one due window with a lease
-> existing observation/provider policy performs only the allowed calls
-> existing alert rules evaluate the stored source-backed snapshot
-> one deduplicated in-app trigger/audit result is persisted
-> Account A sees schedule, source, quota, freshness, and failure truth
-> overlapping/retried invocations create no duplicate run or trigger
-> Account B sees none of Account A's scheduler state
-> kill switch or provider outage stops work without erasing last-known-good
```

One complete schedule is more valuable than adding more local rule types,
commands, or architecture panels. Email/SMS/push/webhook delivery remains
outside this phase.

## Deployment Evidence

Supabase documents Cron as a `pg_cron`-backed scheduler that records job run
status and can invoke an Edge Function. It recommends no more than eight
concurrent jobs and ten minutes per job. The current Free Edge Function limits
are 150 seconds wall clock and two seconds CPU per request. The pilot must stay
well below those ceilings, use authenticated service-to-service invocation, and
store secrets only in the hosted secret boundary:

- https://supabase.com/docs/guides/cron
- https://supabase.com/docs/guides/functions/schedule-functions
- https://supabase.com/docs/guides/functions/limits
- https://supabase.com/docs/guides/functions/auth
- https://supabase.com/docs/guides/functions/logging
- https://supabase.com/docs/guides/database/vault

The preflight must choose one deployable runner path and document why. Prefer a
thin hosted coordinator invoking existing first-party observation/alert logic;
do not port the whole Python intelligence engine into a second TypeScript
product. If no actual hosted runner can be exercised, keep the phase open and
the product state unavailable.

## Prompt Shape

The prompt follows current Codex guidance: state the desired result first,
include only material context, name the hard boundaries, define exact completion
evidence, keep durable conventions in `AGENTS.md`/skills, and require a final
test/review pass. It uses the repository's preflight, product-parity,
clean-room, visual-QA, release, and next-goal skills rather than duplicating
their full workflows.

