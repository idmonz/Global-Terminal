# Phase 6P Hosted Account Recovery Evidence

Updated: 2026-07-16
Status: complete for the scoped hosted account repository and recovery cutover;
hosted recurring scheduling remains explicitly unverified and disabled

## Evidence Boundary

Phase 6N is verified against the linked Supabase project. Its secure
password-authenticated harness passed all 27 assertions for Account A/B
identity and tenant separation, RLS read/write isolation, composite-parent
integrity, optimistic versioning, immutable audit creation, bounded deletion,
and retained audit isolation. The redacted evidence is:

- `review_workspace/phase6n_hosted_rls_summary.json`
- bytes: 413
- SHA-256:
  `91E55418454259B1B777883510E515A716461D8CBDB3B349C7B5F3300B90FA37`

This inherited evidence does not by itself prove the new Phase 6P aggregate
repository or product recovery journey.

## Implemented Product Boundary

- FastAPI signs in with the Supabase publishable key and derives user, tenant,
  and role from the verified session and membership row.
- The browser receives only an opaque HttpOnly `gt_session` cookie and a
  double-submit `gt_csrf` value. Supabase access/refresh tokens remain inside
  the backend process and are excluded from public payloads, URLs, fixtures,
  screenshots, and logs.
- A bounded `account_continuity.v1` document captures the permitted Watchlist,
  Attention, observation, and Alert Manager rows while stripping identity and
  private-note fields. Restore reinjects identity from the server session.
- Supabase documents use RLS, optimistic aggregate versions, idempotency
  receipts, soft deletion, and immutable fingerprint-only audit rows.
- SQLite remains the active domain store and last-known-good cache. Hosted
  outage produces an explicit queued/offline state; it is never reported as a
  remote save.
- Export, import, replay, conflict resolution, and hosted document deletion are
  bounded same-origin account routes. Owner/member may write; viewer is
  read-only.

## Deployment Evidence

Local and linked migration history are aligned through:

`20260715180000_phase6p_account_continuity.sql`

The linked list contains seven matching local/remote versions from
`20260710105056` through `20260715180000`. Phase 6P creates three account
document/receipt/audit tables and two apply/delete RPCs.

Anonymous access to all three tables and both RPCs is denied. Redacted proof:

- `review_workspace/phase6p_anonymous_denial_summary.json`
- bytes: 254
- SHA-256:
  `C8C75E2FA90FE83C9BA0D14AB148CB80EA7438591F191C34B4C8D4E1FBFE2BBC`

## Verified Local And Product Evidence

- Phase 6P focused account/API/performance plus Phase 6J identity regression:
  28 passed.
- Final Phase 6P account-continuity/security harness tests: 16 passed.
- Full project suite: 1,088 collected tests, all passed.
- Production Next test, lint, TypeScript/build, and high-severity npm audit
  pass; npm reports zero vulnerabilities.
- Controlled production visual proof passes with six screenshots, no overflow,
  no unlabeled controls, no unexpected browser errors, and zero direct provider
  calls. See `docs/PHASE_6P_VISUAL_QA_REPORT.md`.
- Local 100-row capture/restore/status performance is within every budget. See
  `docs/PHASE_6P_TEST_AND_RELEASE_REPORT.md`.

## Hosted Owner-Run Evidence

The 2026-07-15 owner handoff now proves both hosted RLS matrices:

- Phase 6O Alert Manager: `phase6o.hosted.rls.v1`, 578 bytes, SHA-256
  `7A63EE35D26BC3385BED9918DE766976395050B3C924D6590B5F688A6A044517`;
- Phase 6P account document: `phase6p.hosted.rls.v1`, 955 bytes, SHA-256
  `18014C76EDAF55FC60B6E8FF318D805662B2A54F33C42478DC75842549930CD9`.

The Phase 6P hosted latency sample count is 10. Network-inclusive read p50/p95
is 188.366/286.160ms and idempotent RPC p50/p95 is 190.557/221.860ms. Both
matrices report zero market-provider calls.

The first recovery attempts exposed two harness/product defects rather than an
RLS defect: stale subprocess environment propagation and a product-side
minimum-eight-character login check that disagreed with already valid Supabase
accounts. The launcher now injects the exact public Supabase runtime into each
isolated child and restores the parent environment. Login rejects only empty or
over-1,024-character shapes and delegates credential validity to Supabase.
Public failures remain generic; bounded auth-stage diagnostics are available
only to the explicit loopback QA child.

The corrected owner run completed through the ordinary product session path
without a sign-in retry or diagnostic call. Redacted product evidence:

- `review_workspace/phase6p_product_recovery_summary.json`;
- evidence version: `phase6p.product.recovery.v1`;
- bytes: 562;
- SHA-256:
  `3C04B1AFD9014C6EB669623B8B5CDE7622C69E8455007FB5F0DC8ED678DEE00E`;
- `supabase_session`, `server_derived_tenant`, `hosted_write`,
  `new_repository_restore`, `account_b_isolated`, and
  `cleanup_reconciled`: true;
- hosted sign-in retries: 0;
- account diagnostic calls: 0;
- market-provider calls: 0.

The journey created a hosted recovery marker as Account A, proved the hosted
repository was contacted, signed into a fresh product process backed by a
distinct empty SQLite repository, restored the exact marker, proved Account B
could not read it, and reconciled cleanup back to hosted state. It printed no
password, token, email, user ID, tenant ID, or payload row.

The unified handoff then accepted the fresh Phase 6O and Phase 6P RLS evidence
and the product recovery evidence:

- `review_workspace/phase6p_hosted_handoff_summary.json`;
- evidence version: `phase6p.hosted.handoff.v1`;
- bytes: 1,624;
- SHA-256:
  `10CD6CFC07D1703139FC13169F8C411433AAD18FA6B25D2AEFF015338FB4B6D3`;
- inherited Phase 6N, Phase 6O hosted RLS, Phase 6P hosted RLS, product
  recovery, and evidence-freshness assertions: true;
- bounded product recovery elapsed time: 17.845 seconds;
- identifiers redacted: true; secrets printed: false.

An independent post-run scan compared 22 configured sensitive/identity values
from `.env` against both summaries and found zero exact-value hits. This scan
also revalidated all required truth fields, zero-call boundaries, and evidence
freshness without printing any compared value.

The credential-free preflights remain repeatable:

- `review_workspace/phase6p_product_recovery_runtime_preflight_summary.json`;
- `review_workspace/phase6p_hosted_handoff_preflight_summary.json`.

They start an isolated Uvicorn process, prove configured/enabled hosted auth and
route availability while remaining anonymous and `configured-unverified`, and
make zero Supabase credential or market-provider calls. To repeat only this
configuration check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_phase6p_hosted_handoff.ps1 -PreflightOnly
```

To revalidate the successful recovery while reusing only fresh redacted RLS
summaries, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_phase6p_hosted_handoff.ps1 -ResumeRecovery
```

The wrapper prompts for each password as `SecureString`, rejects stale or
wrong-version evidence, allocates available loopback ports, and uses two unique
private repositories. Never paste passwords into chat, source files, `.env`,
command arguments, reports, logs, or screenshots.

## Backup And Recovery Truth

The product offers a bounded JSON account export/import for user-controlled
recovery. It is not a substitute for a database backup. Supabase documents
that Free projects should regularly run `supabase db dump` and retain an
off-site logical backup; paid daily backup or PITR retention is not assumed.
No automatic off-site backup, hosted scheduler, email/SMS/push delivery,
billing, broker action, or autonomous action is enabled in Phase 6P.

## Current Verdict

```text
Phase 6N hosted Account A/B RLS: verified
Phase 6P migration and anonymous denial: verified
Phase 6P implementation/local/performance/visual/release: verified
Phase 6P isolated recovery runtime preflight: verified, zero remote calls
Phase 6P unified hosted handoff preflight: verified, zero remote calls
Phase 6O hosted Alert Manager A/B: verified
Phase 6P hosted document A/B: verified
Phase 6P exact runtime/key/network/query preflight: verified
Phase 6P direct Account A credential/membership: verified
Phase 6P Python credential-shape defect: fixed and regression-tested
Phase 6P product sign-out/new-session recovery: verified
Phase 6P hosted network latency: measured separately, 10 samples
Phase 6P bounded recovery acceptance: verified in 17.845 seconds
Production deployment SLO: not claimed
Hosted recurring scheduler: unverified and disabled
```

Phase 6P is complete for its scoped hosted account repository and recovery
cutover. This is not benchmark parity or full production-hosted readiness:
deployed scheduling, external delivery, multi-region operations, and a
production SLO remain future evidence gates.
