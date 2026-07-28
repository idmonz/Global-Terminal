# Phase 6P Test And Release Report

Updated: 2026-07-16
Status: complete for the scoped Phase 6P hosted account repository and recovery
cutover; hosted scheduling remains unverified and disabled

## Verification

- Phase 6P focused account/API/performance plus identity regression: 28 passed.
- Final Phase 6P account-continuity and harness tests: 16 passed.
- Full Python suite: 1,088 collected tests, all passed.
- `python -m py_compile` for changed Python boundaries: passed.
- `python scripts/export_api_fixtures.py`: 34 fixtures generated.
- `npm --prefix apps/web test`: passed; 30 `phase_2b.v1` fixtures plus runtime
  boundary markers validated.
- `npm --prefix apps/web run lint`: passed.
- `npm --prefix apps/web run build`: passed with static and dynamic App Router
  routes compiled.
- `npm --prefix apps/web audit --audit-level=high`: zero vulnerabilities.
- Phase 6P production visual capture and independent verifier: passed.
- Phase 6P owner-run product recovery and combined hosted handoff: passed.
- Independent summary privacy scan: 22 configured sensitive values checked,
  zero exact-value hits.

Existing warnings are one Starlette TestClient deprecation and two
cointegration collinearity warnings. They are not Phase 6P failures.

The first final-suite run exposed a noisy Phase 6M Attention compose p95 of
79.055ms against its 75ms budget. Removing redundant deep copies of newly
constructed internal rows preserved contract behavior and reduced ten repeated
25-sample compose p95 measurements to a maximum of 52.083ms. The focused
Attention suite and the final full regression rerun then passed.

## Performance

Thirty local samples per timed check:

| Check | p50 | p95 | Budget | Result |
|---|---:|---:|---:|---|
| Capture 100 rows | 16.766ms | 22.773ms | 100ms | PASS |
| Restore 100 rows | 18.863ms | 26.984ms | 175ms | PASS |
| Continuity status | 13.353ms | 15.567ms | 50ms | PASS |

The bounded test bundle contains 100 rows and 21,507 bytes against limits of
1,000 rows and 512,000 bytes. Restore integrity has zero conflicts and zero
market-provider calls. This is the local SQLite serialization benchmark.

The owner-run hosted document matrix separately records 10 network-inclusive
samples: read p50/p95 188.366/286.160ms and idempotent RPC p50/p95
190.557/221.860ms. These values are observation evidence, not a production SLO
claim, and remain separate from local timings.

Performance summary SHA-256:
`A586E792E1C1F66CF3F9DFC6D68DC5273531925254D14BD6BBE5D9B34711700C`.

## Release Hygiene

Accepted post-close release evidence:

- archive: `dist/global_market_terminal_20260716T065437Z.zip`;
- selected project files before manifest: 1,796;
- manifest entries: 1;
- actual ZIP entries: 1,797, exactly matching the manifest;
- bytes: 5,303,249;
- SHA-256:
  `51F0A77D157D6AEA746D8570CF25B346E73B48E77E958D72AD3D135FA90C5F80`.

The archive contains all Phase 6P closure and Phase 6Q roadmap documents plus
the unambiguous count report written before packaging. This checked-in
filename/size/hash record is necessarily post-close and is not self-included in
that same archive.

Security inspection checked 24 configured `.env` values. Exact-value hits are
zero and forbidden entries are empty. `.env`, `.next`, `node_modules`,
`external (2)`, `review_workspace`, databases, and logs are excluded. The
public `.env.example` keeps hosted auth and continuity disabled by default.

## Hosted Acceptance

Phase 6O hosted Alert Manager and Phase 6P hosted document matrices pass. The
isolated product runtime also passes its credential-free startup gate, which
verifies exact public Supabase environment propagation and hosted sign-in
availability without contacting Supabase or a market provider.

Earlier owner attempts identified exact environment-propagation and
`credential-shape-invalid` defects. Both were corrected without changing
generic public errors, server-derived tenancy, CSRF/rate-limit controls, or
browser secret boundaries. Empty and over-1,024-character password shapes remain
bounded; Supabase remains the credential authority.

The final owner run passed through the ordinary product session path with no
retry or diagnostic probe. Account A persisted one hosted marker, a fresh
product process with a distinct empty SQLite repository restored the exact
marker, Account B could not read it, and cleanup reconciled to hosted state.
The bounded journey took 17.845 seconds and made zero market-provider calls.

Accepted redacted evidence:

- `phase6p.product.recovery.v1`: 562 bytes, SHA-256
  `3C04B1AFD9014C6EB669623B8B5CDE7622C69E8455007FB5F0DC8ED678DEE00E`;
- `phase6p.hosted.handoff.v1`: 1,624 bytes, SHA-256
  `10CD6CFC07D1703139FC13169F8C411433AAD18FA6B25D2AEFF015338FB4B6D3`.

The combined handoff confirms inherited Phase 6N, Phase 6O RLS, Phase 6P RLS,
product recovery, and evidence freshness. It deliberately records
`hosted_scheduler_verified=false`; no recurring hosted monitor or external
delivery is claimed.
