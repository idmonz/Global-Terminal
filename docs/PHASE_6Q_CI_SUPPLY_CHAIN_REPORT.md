# Phase 6Q CI And Supply-Chain Report

Updated: 2026-07-30

## Result

The repository now has a deployment-ready local CI contract without claiming a
deployed GitHub run. The quality workflow is secret-free and the scheduler
workflow retains only the four reviewed protected-environment secret names.

## Implemented

- `.github/workflows/quality-gate.yml`: PR, `main`, and manual Python/web gates.
- `.github/action-pins.json`: reviewed release tag, full SHA, and official source
  evidence for checkout, setup-python, and setup-node.
- `.github/dependabot.yml`: bounded weekly GitHub Actions, npm, and pip updates.
- `scripts/validate_github_workflows.py`: fail-closed local/CI validator.
- Existing scheduler checkout/setup actions upgraded from mutable tags to
  reviewed SHA pins; checkout credentials are not persisted and dependency
  caching was removed from the secret-bearing job.
- Deployment preflight and source-release tests now require the quality workflow,
  pin registry, dependency policy, and validator.

## Security Contract

- global workflow permission: `contents: read` only;
- no `pull_request_target`;
- concurrency and per-job timeout required;
- every `uses:` reference must be a reviewed 40-character SHA;
- quality CI may access no GitHub secret;
- scheduler secret names must match exactly Supabase URL/secret plus Alpha
  Vantage and Finnhub keys;
- no provider calls occur during validation or page reads;
- no artifact upload, deployment, package publish, write token, broker action,
  or external notification is introduced.

## Verification

- workflow validator: 2 workflows, 6 action uses, 3 reviewed actions, 0 quality
  secrets, 4 allowlisted scheduler secret names, 0 errors;
- dedicated CI supply-chain tests: 7 passed; four additional hosted-RLS
  handoff/migration tests pass;
- full Python suite: 1,121 tests across 483 files passed in 445.8 seconds;
- web fixture/runtime tests, lint, Next.js 16.2.12 production build, and npm
  high-severity audit passed with 0 vulnerabilities;
- fresh `phase6q.visual.v1`: 24 screenshots, 390px no-overflow, visible focus,
  zero provider requests, direct desktop/mobile/Watchlist inspection passed;
- repeated external audit: 28 archives, 51,305 files, 10,596,233 lines,
  249,590 symbols, 0 read errors, unchanged 18/6/3/1 license matrix.

## Remaining External Gate

Supabase CLI connectivity recovered. The linked project is aligned through all
three Phase 6Q migrations and anonymous access is denied 5/5. The preflight now
reports `remote_migration_applied=true`. Git still has branch `main` but no
first commit or remote, and GitHub CLI is unavailable. Therefore the quality
workflow, scheduler workflow, protected environment, Account A/B Phase 6Q
handoff, and job history remain undeployed or unverified and
`hosted_scheduler_verified=false`.

## 2026-07-30 Deployed Continuation

The historical deployment gap above has narrowed. The public GitHub repository,
both workflows, authenticated CLI, and a passing default-branch Quality Gate
now exist. The exact local continuation passes 1,143 Python tests plus web
test/lint/build/audit, workflow validation, source-release inspection, and Git
publication security scanning.

The hosted observation workflow has seven reviewed full-SHA action uses across
the two workflows. Its scheduled job is now fail-closed at job admission:

- repository variable
  `GLOBAL_TERMINAL_HOSTED_SCHEDULER_OPERATOR_ENABLED` must equal `true`;
- manual dispatch additionally requires Boolean `confirm_run=true`;
- when the repository variable is absent or false, the job is skipped before a
  runner receives secrets or performs provider work;
- the global kill switch remains armed and recurring execution is not claimed.

Earlier deployed scheduled attempts failed before claiming work because the
`phase6q-pilot` environment did not expose the required credentials. Those
failures are retained as honest evidence, not promoted to scheduler
verification. The repository is still public and `main` remains unprotected.
Changing visibility, branch protection, protected-environment policy, or the
operator variable remains an explicit owner security decision.

Current workflow validation reports two workflows, seven action uses, three
reviewed actions, zero quality-gate secret references, four allowlisted
scheduler secret names, zero provider calls, and zero errors. Phase 6Q remains
active until one bounded deployed run and its replay/failure/recovery/cleanup
evidence pass the hosted verifier.
