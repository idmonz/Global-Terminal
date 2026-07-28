# Phase 6Q Remote Migration And RLS Preflight Report

Updated: 2026-07-27

## Verdict

The linked Supabase project is now aligned through all three Phase 6Q
migrations:

- `20260727143000`: hosted scheduler control, schedule, run, audit, RLS, and
  user/service RPC boundary;
- `20260727190000`: one-active-schedule partial unique index;
- `20260727191500`: catalog-resolved removal of the legacy full-owner unique
  constraint whose generated name was truncated by PostgreSQL.

This is remote schema evidence, not hosted scheduler evidence. The operator
gate remains off, the global kill switch remains armed, no service credential
was used locally, and no market-provider call or worker invocation occurred.

## Verified Evidence

- `supabase migration list --linked` reports matching Local/Remote versions for
  all three Phase 6Q migrations.
- The read-only deployment preflight reports `remote_probe_status=reachable`
  and `remote_migration_applied=true`.
- `scripts/verify_phase6q_remote_anonymous_denial.py` receives HTTP 401 for all
  four scheduler tables and the user schedule RPC: 5/5 denied, zero mutation,
  zero provider calls, and no identifier or key output.
- Local actual PostgreSQL conformance now creates, deletes, replaces, and
  deletes a second schedule in the same rolled-back transaction. This proves
  deleted history no longer permanently blocks a future active schedule while
  the one-active-schedule boundary remains.

## Password-Authenticated Hosted Gate

The next safe command is:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test-phase6q-hosted-scheduler-rls.ps1
```

It prompts for Account A/B passwords as `SecureString` and does not print the
passwords, tokens, emails, user IDs, tenant IDs, payload rows, project
identifier, or key. It uses only each account's user JWT, temporarily adds two
bounded parent rows to Account A's existing `research-continuity` document,
and verifies:

- Account A schedule create/read and explicit enable/pause/kill/delete;
- optimistic conflict behavior;
- Account B read/update/delete/forge denial across schedule, run, and audit;
- immutable lifecycle audit isolation;
- replacement creation after soft deletion;
- safe deleted terminal state and exact restoration of Account A's original
  account-document payload.

The harness never reads a service key, never changes the scheduler control
row, never invokes the hosted worker, and makes zero market-provider calls. A
redacted pass is written to
`review_workspace/phase6q_hosted_rls_summary.json`.

## Remaining Hosted Blockers

- Account A/B password-authenticated Phase 6Q RLS handoff has not yet been run.
- The repository still has no first commit, private origin, or authenticated
  GitHub CLI.
- Quality and scheduler workflows are not deployed on a default branch.
- The protected `phase6q-pilot` environment and four secret names are not
  verified.
- No real scheduled source-backed run, replay, failure/LKG, kill/recovery, job
  history, or cleanup handoff has passed.

Therefore `hosted_scheduler_verified=false` remains mandatory.
