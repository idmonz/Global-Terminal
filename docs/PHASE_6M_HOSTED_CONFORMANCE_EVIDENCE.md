# Phase 6M/6N Hosted Conformance Evidence

Updated: 2026-07-15

## Evidence Boundary

The linked Supabase project, account emails, user IDs, tenant IDs, API keys,
passwords, and access tokens are intentionally redacted. Local `.env` contains
the six manual QA identifiers and remains outside release packaging.

This document distinguishes four different claims:

1. **Phase 6M historical A/B RLS:** verified.
2. **Current Account A/B bootstrap and tenant separation:** verified.
3. **Phase 6N schema deployment and anonymous denial:** verified.
4. **Phase 6N password-authenticated hosted A/B CRUD/RLS:** verified.

## Historical Phase 6M Evidence

- Account A/B bootstrap, distinct users, and distinct personal tenants: PASS.
- Account A preference, watchlist, sync receipt, and Attention CRUD: PASS.
- Account B reads, updates, deletes, and cross-tenant inserts against Account A:
  BLOCKED.
- Account A data integrity after Account B attempts: PASS.
- Test-row cleanup: PASS.

## Current Bootstrap Evidence

On 2026-07-14, `scripts/bootstrap-phase6m-users.ps1` authenticated both test
accounts and invoked `global_terminal_bootstrap_personal_tenant` successfully.

- Account A login/bootstrap: PASS.
- Account B login/bootstrap: PASS.
- User IDs are distinct: PASS.
- Tenant IDs are distinct: PASS.
- No password, API key, or access token was printed: PASS.

## CLI And Migration Evidence

- Docker Desktop and the local Supabase database are operational.
- The repository is linked to the intended hosted project.
- Historical Phase 6J-6M schema was compared with a fresh remote schema dump.
  Tables, columns, constraints, and RLS policies matched; hosted-only default
  privilege/event-trigger differences were classified separately.
- The four historical migration versions were registered as already applied.
- `20260714230000_phase6n_observation_and_hosted_hardening.sql` was the only
  dry-run candidate and was pushed successfully.
- `supabase migration list --linked` now shows all five local/remote versions
  aligned.
- A second `supabase db push --linked --dry-run` reports the remote database is
  up to date.

The experimental pg-delta catalog cache emitted a missing generated-CA warning
after the successful push. It did not roll back SQL. Local config now disables
that alpha engine and uses the stable migration/dump path.

## Backup Evidence

Pre-deployment evidence is stored only under `review_workspace/`, which is not
part of the release archive.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Phase 6M remote schema | 60,734 | `5C8D59986A36ECA839B5D08AE6EE6FEB83D0CC365CA682C4F0F911B02B4EB6E3` |
| Phase 6M remote data | 20,721 | `C83379A12C40BEE97E5E6182062B3739B4753210D578860156380DE51435C352` |
| Phase 6N post-deploy schema | 79,053 | `D3E36FFD545E4DC0051722A357B9E036F116C200177FAD545455285D054F0097` |

The data dump is private recovery material. Its contents must not be committed,
published, copied into screenshots, or included in release ZIPs.

## Phase 6N Schema And Permission Evidence

- `global_terminal_*` hosted table count: 18.
- RLS enabled on all 18 tables: PASS.
- New observation tables present: runs, snapshots, quota ledger, run audit.
- Anonymous table grants across all product tables: 0.
- Authenticated observation grants are least-privilege:
  - runs: select/insert/update/delete;
  - snapshots: select/insert;
  - quota ledger: select/insert;
  - run audit: select only.
- Composite `(tenant_id, owner_user_id, run_id)` parent integrity: PRESENT.
- Audit trigger for insert/update/delete: PRESENT.
- Parent deletion cannot cascade-delete audit evidence: PASS by schema review.
- All four Phase 6N REST endpoints are present and reject anonymous reads with
  HTTP 401.

## Local Functional RLS Evidence

The full five-migration chain passed a clean `supabase db reset`. The durable
local harness then passed:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test-phase6n-local-rls.ps1
```

It proves real PostgreSQL behavior, not text matching:

- Account A can create/read its run, snapshot, quota, and audit evidence.
- Account B sees zero Account A rows.
- Cross-tenant writes and cross-tenant child-parent linkage fail.
- Authenticated users cannot forge audit rows.
- A stale optimistic update changes zero rows.
- Child rows cascade on run deletion while audit evidence survives.
- The entire test rolls back and leaves no local QA rows.

## Hosted A/B Result

On 2026-07-15, the secure-password hosted harness completed all 27 positive and
negative assertions. It made zero market-provider calls and produced a
redacted 413-byte summary:

| Field | Result |
|---|---|
| Evidence version | `phase6n.hosted.rls.v1` |
| Account isolation | PASS |
| Optimistic conflict | PASS |
| Composite parent integrity | PASS |
| Audit immutability | PASS |
| Audit retained after parent delete | PASS |
| Provider calls | 0 |
| Identifiers redacted | PASS |
| Secrets printed | false |

Summary SHA-256:
`91E55418454259B1B777883510E515A716461D8CBDB3B349C7B5F3300B90FA37`.

The verified matrix includes Account A create/read/update/delete, Account B
zero-row reads and zero-row mutations, HTTP 403 cross-tenant insert denial,
HTTP 409 composite-parent denial, HTTP 403 audit-forgery denial, stale-version
zero-row update, bounded child deletion, retained audit evidence, and retained
audit isolation from Account B.

The run is reproducible from the repository root. It securely prompts for both
passwords and never writes them to disk:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test-phase6n-observation-rls.ps1
```

Verified completion marker:

```text
Phase 6N hosted RLS conformance passed.
Redacted summary: review_workspace/phase6n_hosted_rls_summary.json
```

The script retains the append-only audit trail for the deleted test run by
design. The verified result confirms that no run, snapshot, or quota row
remains.

## Remaining Hosted Gates

- Session revocation and expiry behavior: PENDING.
- Hosted outage and recovery behavior: PENDING.
- Backup restore drill: PENDING.
- Bounded export/deletion and tombstone behavior: PENDING.
- Hosted latency/SLO measurement: PENDING.
- Final exact-value and release scan after the redacted summary: PENDING.

## Current Truth

```text
Phase 6M historical basic hosted Auth/RLS: verified
current Account A/B bootstrap and tenant separation: verified
Phase 6N migration/schema/permissions/anonymous denial: verified
Phase 6N authenticated hosted A/B database conformance: verified
full hosted persistence and recovery readiness: not verified
```
