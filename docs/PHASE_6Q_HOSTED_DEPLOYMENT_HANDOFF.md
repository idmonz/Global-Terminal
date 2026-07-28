# Phase 6Q Hosted Deployment Handoff

Updated: 2026-07-28

## Current Truth

The scheduler control plane, Python worker, additive Supabase migration, local
Postgres/RLS conformance, account-bundle recovery, API/UI contract, visual
evidence, and bounded performance harness are implemented. The hosted worker is
still **disabled and unverified**. A local process, fixture, successful HTTP
response, or checked-in workflow file is not a deployed recurring scheduler.

The selected pilot runner is one private GitHub Actions scheduled Python job.
It reuses the Phase 6N observation coordinator and Phase 6O alert evaluator.
No second TypeScript/Deno market engine is introduced.

The linked project is remote-aligned through the three Phase 6Q migrations, the
anonymous-denial probe passes 5/5, and the owner-run Account A/B user-session
RLS harness passes with zero cross-tenant rows and zero provider calls. The
independent verifier accepts the fresh redacted summary. Deployed worker proof
remains outstanding.

## Safety Defaults

- `global_terminal_hosted_scheduler_control.operator_enabled=false`
- `global_terminal_hosted_scheduler_control.global_kill_switch=true`
- `global_terminal_hosted_scheduler_control.hosted_scheduler_verified=false`
- one concurrent workflow, one saved Watchlist, at most five symbols, at most
  sixteen provider calls, bounded attempts, and a four-minute workflow timeout
- no provider request from page reads, schedule edits, or triage
- no service credential in browser code, `NEXT_PUBLIC_*`, URLs, fixtures,
  screenshots, reports, or release archives

## Step 1: Run The Read-Only Preflight

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_phase6q_hosted_preflight.ps1 -ProbeLinked -ProbeGitHub
```

This prints only boolean checks and blocker codes. It does not prompt for an
account password, mutate Supabase/GitHub, call a market provider, or reveal the
project ref, repository name, emails, UUIDs, or keys. The redacted result is
written to `review_workspace/phase6q_hosted_deployment_preflight_summary.json`.

## Step 2: Apply The Additive Supabase Migration

Do this only after `supabase link` points to the intended project. Never use a
remote reset.

```powershell
supabase migration list --linked
supabase db push --linked
supabase migration list --linked
```

The second list must show `20260727143000`, `20260727190000`, and
`20260727191500` in both Local and Remote columns.
If the login-role service returns a timeout, stop and retry later; do not use a
destructive workaround. The migration starts with the operator gate off and
the global kill switch armed.

After Local and Remote align, verify that an anonymous publishable-key client
cannot read the control/schedule/run/audit tables or execute the user schedule
RPC:

```powershell
python scripts/verify_phase6q_remote_anonymous_denial.py
```

All five checks must return 401/403. This probe prints no URL, project reference,
key, account identifier, or response body and performs zero provider calls.

The current linked project passes these migration and anonymous-denial checks.
Re-run them after any schema change; do not infer user-session RLS from anonymous
denial.

## Step 2B: Prove Account A/B Scheduler RLS

Run the bounded user-JWT handoff before creating a server key or deploying a
worker. The script resolves the repository from its own location, so the
absolute command below works from any PowerShell directory:

```powershell
$scriptPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "TV 창업 스크립트\Global Terminal\scripts\test-phase6q-hosted-scheduler-rls.ps1"
powershell -ExecutionPolicy Bypass -File $scriptPath
```

Enter Account A and Account B passwords only into the local `SecureString`
prompts. The script prints no credential, token, email, UUID, tenant, payload,
or project identifier. It never reads a service key, changes the scheduler
control row, or calls a market provider.

A pass must prove create/read, optimistic conflict, explicit enable/pause/kill/
delete, Account B isolation and forge denial, immutable audit isolation,
replacement after soft deletion, and exact restoration of Account A's original
`research-continuity` payload. The redacted result is written to
`review_workspace/phase6q_hosted_rls_summary.json`.
The harness then runs an independent fail-closed verifier over that redacted
file. It rejects stale evidence, unexpected fields, non-zero provider/cross-
tenant counts, secret exposure, or any attempt to promote hosted scheduler
verification:

```powershell
python scripts/verify_phase6q_hosted_rls_summary.py review_workspace/phase6q_hosted_rls_summary.json
```

If the script warns that cleanup or document restoration failed, keep the
global kill switch armed and do not continue to Step 3.

The 2026-07-28 owner run passed and is summarized without identifiers in
`docs/PHASE_6Q_HOSTED_RLS_EVIDENCE_REPORT.md`. Re-run it after any scheduler RLS
or account-document migration; do not reuse stale evidence.

## Step 3: Create A Dedicated Supabase Server Key

In Supabase Dashboard open **Project Settings > API Keys** (or the project's
Connect dialog), create a dedicated secret key for this worker, and store it as
`SUPABASE_SECRET_KEY` only in the GitHub `phase6q-pilot` environment.

New `sb_secret_*` keys are opaque API keys. The worker correctly sends them in
the `apikey` header and does not send them as bearer JWTs. They bypass RLS and
must never be used in a browser, committed, pasted into a URL, or printed. Use
a separate key for this worker so it can be revoked independently.

Official reference:
https://supabase.com/docs/guides/getting-started/api-keys

## Step 4: Publish A Private GitHub Repository Safely

The repository currently needs a real commit and private remote before the
workflow can exist on the default branch. `.gitignore` excludes `.env`, external
archives, local Supabase state, screenshots, databases, Node/Python caches, and
release artifacts. Review the staged file list before committing:

```powershell
git status --short
git check-ignore -v .env "external (2)" review_workspace dist supabase/.temp
git add -A
git status --short
```

Do not continue if `.env`, `external (2)`, `review_workspace`, `dist`, a database,
or `supabase/.temp` is staged. Create a **private** repository, commit the reviewed
source, and push the default branch. GitHub's `schedule` event only runs a
workflow present on the default branch and can be delayed or dropped during high
load, so product truth remains at-least-once/idempotent rather than exactly-once.

Before enabling the scheduler, require the `Quality gate` workflow to pass on
the default branch. It runs the Python, web, fixture, release, and dependency
security gates without receiving account, Supabase, or market-provider secrets.
All workflow actions are pinned to reviewed full commit SHAs recorded in
`.github/action-pins.json`; `scripts/validate_github_workflows.py` fails closed
on mutable tags, unknown actions, write permissions, secret use in quality CI,
or missing timeout/concurrency controls. Dependabot changes to action pins need
deliberate review of both the workflow and pin registry before merge.

Official reference:
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

## Step 5: Configure The Protected GitHub Environment

Create the environment `phase6q-pilot`. Add these environment secrets:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `ALPHAVANTAGE_API_KEY`
- `FINNHUB_API_KEY`

Use an environment reviewer where the account plan supports it. GitHub does not
release environment secrets to the job until required approval completes. Never
put secret values in workflow YAML or repository variables.

Official references:
https://docs.github.com/en/actions/reference/security/secrets
https://docs.github.com/en/actions/reference/security/secure-use

## Step 6: Manual Pilot Before Recurrence

1. Keep the database operator gate off and kill switch on.
2. Dispatch `Phase 6Q hosted observation` manually. It must return `disabled`
   or `killed`, claim no work, and spend zero provider calls.
3. Create one Account A schedule in disabled state, then explicitly consent in
   the Alert Manager.
4. In a short owner-attended window, set `operator_enabled=true` and
   `global_kill_switch=false` using the privileged operator channel.
5. Dispatch once. Observe one due claim, one source-backed snapshot, one alert
   evaluation/trigger, and the GitHub job history.
6. Dispatch the same window again. It must produce no duplicate effect and no
   additional provider call.
7. Exercise the controlled provider-failure, expired-lease recovery, and kill
   paths, then return the global kill switch to `true`.
8. Delete temporary schedule/run rows through bounded cleanup while retaining
   immutable audit evidence.

Do not leave an operator-attended pilot enabled just to obtain a green badge.

## Step 7: Produce And Verify Hosted Evidence

The owner handoff must write a redacted
`phase6q.hosted.handoff.v1` JSON summary. It is accepted only when every
deployment, job-history, source, trigger, A/B isolation, overlap, idempotency,
quota, failure/LKG, kill, lease recovery, cleanup, audit, zero-read-call, and
privacy assertion is present.

Start from `docs/PHASE_6Q_HOSTED_EVIDENCE_TEMPLATE.json`. The checked-in
template intentionally fails verification and contains no account or deployment
identifier. Populate only redacted counts, clocks, versions, and assertions
produced by the real handoff; never edit it into a claimed pass by observation
alone.

```powershell
python scripts/verify_phase6q_hosted_evidence.py review_workspace/phase6q_hosted_handoff_summary.json
```

Only after that verifier passes may both settings be changed:

```text
GLOBAL_TERMINAL_HOSTED_SCHEDULER_VERIFIED=true
GLOBAL_TERMINAL_HOSTED_SCHEDULER_EVIDENCE_PATH=review_workspace/phase6q_hosted_handoff_summary.json
```

Evidence expires after 168 hours by default, preventing an old pilot from being
presented as current hosted verification. Availability and live source health
remain separate runtime states even while deployment evidence is valid.

## Rollback

1. Set `global_kill_switch=true` immediately.
2. Set `operator_enabled=false`.
3. Disable the GitHub workflow schedule or remove its environment approval.
4. Revoke the dedicated Supabase secret key if compromise is suspected.
5. Preserve immutable audit and redacted job evidence.
6. Keep `GLOBAL_TERMINAL_HOSTED_SCHEDULER_VERIFIED=false` until a fresh complete
   handoff passes again.

Do not drop shared account, observation, alert, or audit tables during rollback.
