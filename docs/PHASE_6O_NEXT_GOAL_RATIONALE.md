# Phase 6O Next Goal Rationale

Updated: 2026-07-15

## Decision

Select **Phase 6P: Hosted Account Repository And Recovery Cutover**.

Phase 6O now has a useful local-first Alert Manager, a deployed RLS schema,
local actual-RLS evidence, remote anonymous denial, a secure hosted A/B harness,
strong visual proof, and bounded performance. The remaining commercial
bottleneck is not another rule type. It is that the web product still relies on
local-test identity and process-local repositories.

## Evidence

- Phase 6N password-authenticated hosted observation A/B conformance passes.
- Phase 6O remote migration history is aligned, but its password-authenticated
  A/B harness still needs one owner-run execution.
- `SupabaseTenantResearchPersistence` remains explicitly unavailable and no
  production repository carries Watchlist, Attention, observation, or alert
  state across devices.
- The optional local worker is useful for bounded QA but cannot be called an
  always-on hosted service.
- Adding external notification channels before account persistence/recovery is
  proven would enlarge risk without closing the user trust gap.

## Target Journey

```text
Supabase sign in -> open saved Watchlist/Attention/Alert Manager
-> read and mutate tenant-owned hosted state
-> sign out and restore the same state in a new session
-> prove Account B isolation
-> survive API/database outage with honest read-only/local continuity
-> recover and reconcile without duplicate or lost audit evidence
```

Hosted Cron and external notification delivery remain later phases. Phase 6P
may expose scheduler readiness, but it must not enable recurring jobs until the
account repository, A/B matrix, outage/recovery, backup/restore, deletion, and
observability gates pass.

## Prompt Shape

The next prompt follows current Codex guidance: lead with the desired result,
name only material context, state output and hard boundaries, point to exact
files, and require a final verification pass. Repository skills remain focused,
progressively disclosed workflows rather than duplicating all instructions in
the prompt.

