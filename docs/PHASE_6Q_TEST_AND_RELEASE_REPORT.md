# Phase 6Q Test And Release Report

Updated: 2026-07-30

## Verdict

The Phase 6Q local implementation and release candidate pass their bounded
product, database, visual, performance, privacy, external-audit, and packaging
gates. Phase 6Q itself remains active because no default-branch hosted runner
has yet produced fresh deployed job, source, Account A/B, replay, failure,
recovery, and cleanup evidence.

`hosted_scheduler_verified` remains `false`. The scheduler remains disabled by
default and the global kill switch remains armed.

## Product And Contract Gates

- Phase 6Q focused contract, worker, operations, API, harness, and release tests:
  pass.
- Full Python suite: 1,121 tests across 483 files passed in 445.8 seconds; only the
  existing Starlette/httpx deprecation and cointegration collinearity warnings
  remain.
- Python compile: `python -m compileall -q lib backend scripts` passed.
- Fixture export: 35 JSON files generated; the web validator accepted 31
  `phase_2b.v1` fixtures.
- Web: `npm test`, `npm run lint`, and the Next.js 16.2.12 production build
  passed.
- Dependency audit: zero high-severity npm vulnerabilities.
- Agent harness and smoke imports: passed with one active Phase 6Q plan and six
  repository skills.

## CI And Supply-Chain Gate

- `.github/workflows/quality-gate.yml` adds bounded Python and web jobs for
  pull requests, `main`, and manual dispatch without any secret reference.
- Both workflows grant only `contents: read`, define concurrency and per-job
  timeouts, and disable checkout credential persistence.
- Six action uses match three reviewed full commit SHAs in
  `.github/action-pins.json`; official release tag and source URL evidence is
  retained beside each pin.
- The independent validator reports two workflows, six action uses, three
  reviewed actions, zero quality-gate secrets, four allowlisted scheduler
  secret names, zero provider calls, and zero errors.
- Seven dedicated CI tests plus four hosted-RLS/migration tests prove the
  passing contract and rejection of mutable
  action tags, unknown actions, write permissions, `pull_request_target`,
  missing job timeouts, and quality-CI secret references.
- Weekly bounded Dependabot policies cover GitHub Actions, npm, and pip.
- These are local repository checks. Neither workflow is committed, deployed,
  or observed on GitHub yet.

## Database And Hosted Boundary

- `supabase db lint --local --level warning`: zero findings.
- Local actual-PostgreSQL conformance passed for tenant RLS, lease and
  heartbeat, overlap suppression, idempotent replay, quota caps, source/LKG,
  provider failure, kill switch, lease recovery, audit retention, cleanup, and
  replacement creation after soft deletion.
- The deployment preflight is intentionally read-only and red. It found no Git
  commit, remote, authenticated GitHub CLI, protected environment-secret proof,
  or deployed workflow. The linked probe is now reachable and reports all three
  Phase 6Q migrations remote-aligned. Anonymous clients are denied 5/5 across
  the four scheduler tables and user RPC with zero provider calls.
- `scripts/test-phase6q-hosted-scheduler-rls.ps1` is ready to prove Account A/B
  user-JWT isolation, optimistic conflict, immutable audit, safe lifecycle,
  replacement, and exact account-document restoration. It requires local
  SecureString password entry and has not yet produced hosted A/B evidence.
- The independent hosted-evidence verifier requires all 15 assertions plus a
  deployed/default-branch runner, bounded counts, HTTPS source evidence, safe
  terminal state, redaction, and evidence freshness. Partial flag files cannot
  promote the hosted status.

## Visual And Performance Evidence

- `phase6q.visual.v1`: 24 screenshots passed after direct desktop and 390px
  mobile inspection.
- Initial HTML: 49,002 bytes.
- Desktop navigation: 168px; mobile root: 390px with no horizontal overflow.
- Duplicate IDs, unlabeled controls, hidden provider calls, and unexpected
  browser errors: zero.
- Keyboard focus is visibly 2px and two live regions are present.
- Scheduler read/compose benchmark: 200 samples, p50 6.894ms, p95 11.412ms,
  mean 7.659ms against a 75ms p95 limit; safe-default p95 0.010ms.
- One full-suite run exposed a Phase 6O 30-sample timing outlier at 76.745ms.
  Five isolated repetitions measured evaluation p95 at 37.626-62.744ms. The
  gate keeps the 75ms limit and increases its sample size to 50; the final full
  suite passes, reducing sensitivity to one transient system stall without
  weakening the threshold.

## External And Clean-Room Gate

- Full archive audit: 28 archives, 51,305 files, 39,622 text candidates,
  10,596,233 lines, 249,590 symbols, and zero read errors.
- License classification remains 18 direct-use, 6 behavior-only, 3
  needs-review, and 1 blocked.
- Archive SHA comparison against the Phase 6O baseline found zero changes.
- No blocked source, external archive, generated review evidence, or private
  data is included in the release archive.

## Release Candidate

- Archive naming: `dist/global_market_terminal_<UTC timestamp>.zip`.
- Exact final archive name, size, entry count, and SHA-256 are generated only
  after this report is included; they must be taken from the final build output
  and independent post-build inspection rather than embedded recursively here.
- Configured sensitive values checked: 24.
- Exact sensitive-value hits: 0.
- Forbidden entries: 0.
- Required Phase 6Q workflow, worker, operation contract, migration, handoff,
  quality workflow, action pin registry, dependency policy, and evidence
  verifier missing from ZIP: 0.

The release builder previously omitted `.github`. Phase 6Q fixed the allowlist,
added the private workflow to required release tests, rebuilt the archive, and
re-ran both security and independent ZIP-entry checks.

## Remaining Completion Gate

Follow `docs/PHASE_6Q_HOSTED_DEPLOYMENT_HANDOFF.md`. Run the password-authenticated
Phase 6Q A/B RLS handoff, commit to a private repository, configure the protected
`phase6q-pilot` GitHub environment, exercise one bounded manual/default-branch
pilot and controlled replay/failure/recovery/cleanup sequence, then validate the
fresh redacted evidence with `scripts/verify_phase6q_hosted_evidence.py`.

Until that evidence passes, do not archive Phase 6Q, enable recurring provider
work, claim hosted reliability, or advance the benchmark score to 5.

## 2026-07-30 World Map V2 Continuation

The historical 2026-07-27 figures above remain the original Phase 6Q release
gate. The current continuation was re-run after the World Map v2 and scheduler
operator-gate changes:

- full Python suite: 1,143 tests across 486 files passed in 413.3 seconds;
- focused map/provider/API suite: 48 passed;
- focused scheduler/workflow/map suite: 33 passed;
- `python -m compileall -q lib backend scripts`: passed;
- web fixture/runtime tests, lint, Next.js production build, and npm audit:
  passed with zero vulnerabilities;
- `phase6q.world-map.v2.visual.v1`: five independently verified captures,
  283 bounded events, 275 source-backed coordinates, zero unexpected browser
  errors, no horizontal overflow, and an explicit tile-failure fallback;
- repeated external audit: 28 archives, 51,305 files, 39,622 text candidates,
  10,596,233 lines, 249,590 symbols, zero read errors, and zero ZIP fingerprint
  changes;
- Git publication audit: 1,845 candidate files, 141,456,990 bytes, 25
  configured values, zero exact secret hits, zero forbidden paths, and zero
  unreviewed token hits;
- release security audit: 24 configured values, zero exact hits, and zero
  forbidden entries.

The inspected release candidate is
`dist/global_market_terminal_20260730T094447Z.zip`: 57,610,245 bytes, 1,856
archive entries including the manifest, SHA-256
`26FA79ADEDF0796FE7F3F8DC1C3F99D33F0FBC12C7AB6B1D071E69EFC2E7D565`.

These gates improve the local and distributable product evidence. They do not
replace the missing successful deployed scheduler run, so Phase 6Q remains
active and `hosted_scheduler_verified` remains `false`.
