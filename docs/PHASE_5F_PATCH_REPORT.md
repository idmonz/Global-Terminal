# Phase 5F Patch Report

Updated: 2026-06-19

Phase 5F was audit-first. Only low-risk reconciliation patches were made.

## Patch 1: Release Architecture Reconciliation

File: `scripts/build_release_zip.py`

Change:

- include `apps`, `backend`, and `requirements-api.txt`;
- exclude `.next`, `.turbo`, `node_modules`, `build`, and `coverage`;
- preserve existing external/private/secret/model/cache exclusions.

Reason: the release ZIP previously omitted the documented commercial web and optional API architecture.

## Patch 2: External Audit CSV Release Boundary

File: `scripts/build_release_zip.py`

Change:

- exclude CSV files from release unless under `static/index_constituents/` or `tests/fixtures/`.

Reason: the required Phase 5F full external inventory belongs in the repository audit record, not the distributable source package. This also restored the existing Goal 12B release hygiene invariant.

## Patch 3: Release Regression Tests

File: `tests/test_phase5f_release_includes_web_backend.py`

Coverage:

- required web/backend/API files selected and packaged;
- generated web trees excluded;
- external/private/secret paths excluded;
- Phase 5F external inventory CSV excluded.

## Patch 4: Deterministic External Audit

File: `scripts/audit_phase5f_external.py`

Outcome:

- 19 archives, 40,932 files, 7,968,399 lines, and 170,395 symbols inventoried;
- duplicate root `external.zip` not double-counted;
- license evidence and exact paths recorded;
- no claim of full semantic manual review.

## Non-Patches

No product feature, provider claim, chart/map behavior, auth, billing, persistence, execution path, or external runtime source was added during Phase 5F.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
