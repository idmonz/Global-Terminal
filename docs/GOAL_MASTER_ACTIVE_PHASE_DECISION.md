# Goal Master Active Phase Decision

Updated: 2026-07-30

## Active Plan

**Phase 6Q: Hosted Observation Scheduler And Alert Operations Pilot.**

Exactly one active execution plan remains at
`docs/exec-plans/active/PHASE_6Q.md`. Do not select Phase 6R or archive Phase 6Q
until one real hosted source-backed schedule run, replay/overlap suppression,
failure/LKG, kill/recovery, Account A/B isolation, cleanup, job history, and
independent redacted evidence all pass.

## Completed Foundation

Phase 6N completed the bounded source-backed observation run and Attention
handoff. Phase 6O completed tenant-safe in-app alert rules, stored-observation
evaluation, trigger history, and a bounded local worker. Phase 6P completed the
hosted account-continuity repository and real two-repository recovery proof.

Phase 6Q has completed its local control plane, additive Supabase migrations,
actual-Postgres conformance, password-authenticated hosted A/B RLS, API/UI
surface, local performance, 24-capture scheduler visual matrix, external audit,
release audit, Git publication, and a passing default-branch Quality Gate.

The World Map v2 continuation is also complete inside Phase 6Q. It adds NASA
EONET, preserves a bounded 283-event EONET/USGS/static surface, clusters by zoom,
supports regional and shareable viewport state, collapses layers on mobile, and
falls back honestly when OSM tiles fail. Its five screenshots and independent
verifier pass. This improves product depth but does not close Phase 6Q.

## Exact Open Gate

The GitHub scheduler workflow exists and scheduled attempts reached hosted
runners, but they failed before a due claim because pilot environment secrets
were absent. The repository is public and `main` is unprotected. The workflow
now fails closed unless repository variable
`GLOBAL_TERMINAL_HOSTED_SCHEDULER_OPERATOR_ENABLED=true`; manual dispatch also
requires `confirm_run=true`.

Keep the variable false, database operator gate off, and global kill switch
armed until the owner decides repository privacy/protection, configures the
protected `phase6q-pilot` environment, and attends the bounded pilot. A skipped
job, workflow file, fixture, local process, or HTTP 200 is not hosted monitoring
proof.

The durable master goal remains active and benchmark parity is not claimed.
