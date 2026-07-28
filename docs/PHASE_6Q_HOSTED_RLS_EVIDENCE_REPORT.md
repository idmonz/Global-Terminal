# Phase 6Q Hosted Scheduler RLS Evidence

Updated: 2026-07-28
Status: passed for Account A/B user-session RLS; hosted worker remains disabled and unverified

## Authoritative Evidence

- harness: `scripts/test-phase6q-hosted-scheduler-rls.ps1`
- redacted runtime summary: `review_workspace/phase6q_hosted_rls_summary.json`
- evidence version: `phase6q.hosted-rls.v1`
- captured at: `2026-07-28T08:53:07.6862312+00:00`
- independent verifier: `scripts/verify_phase6q_hosted_rls_summary.py`
- verifier result: passed, zero reasons, zero provider calls, zero unexpected fields

The owner entered Account A and Account B passwords only through local
`SecureString` prompts. No password, token, email, UUID, tenant identifier,
payload row, project identifier, or provider response was written to the
evidence file or printed by the harness.

## Proven

- both configured identities authenticated and were distinct;
- both server-derived tenant scopes were distinct;
- Account A created, read, enabled, paused, killed, and soft-deleted one bounded
  tenant-qualified schedule;
- Account B observed zero Account A schedule, run, and audit rows;
- Account B could not insert, update, delete, or forge Account A scheduler
  state;
- stale optimistic writes were rejected;
- authenticated clients could not forge immutable scheduler audit rows;
- the schedule lifecycle produced retained audit evidence isolated from
  Account B;
- a soft-deleted schedule no longer blocked one bounded replacement;
- the replacement returned to the deleted safe state;
- Account A's original `research-continuity` document was restored exactly;
- temporary parent rows were removed and the original document was re-read;
- the operator gate was not changed, the hosted worker was not invoked, and
  market-provider calls remained exactly zero.

The independent verifier additionally rejects missing or unexpected fields,
non-zero cross-tenant/provider counts, stale or future-dated evidence, secret
exposure, and any attempt to promote hosted scheduler verification from this
RLS-only run.

## Not Proven

This evidence does not prove a committed or deployed GitHub workflow, protected
environment secrets, a source-backed scheduled observation, job history,
overlap/replay behavior in the deployed runner, provider outage/LKG handling,
lease recovery, deployed cleanup, or recurring availability. Therefore:

```text
hosted_scheduler_verified=false
operator_enabled=false
global_kill_switch=true
```

remain the truthful defaults.

## Remaining Phase 6Q Gates

1. Create and review one local Git commit, then publish it to a private GitHub
   repository on the default branch.
2. Authenticate GitHub CLI and prove the secret-free `Quality gate` passes on
   that default branch.
3. Create the protected `phase6q-pilot` environment and add only the four
   allowlisted secret names.
4. Run the bounded disabled/killed pilot, one source-backed due window,
   idempotent replay, controlled failure/LKG, lease recovery, kill, and cleanup.
5. Generate and independently verify fresh
   `phase6q.hosted.handoff.v1` evidence before changing any hosted-verification
   flag.
