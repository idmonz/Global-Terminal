# Phase 5F Release Reconciliation Report

Updated: 2026-06-19

## Initial Blocker

The release script and release manifest contradicted the documented product architecture. The ZIP omitted the entire commercial web shell, optional backend, and API requirements even though ROADMAP described them as completed product surfaces.

Initial evidence:

- `apps/` entries: 0
- `backend/` entries: 0
- `requirements-api.txt`: absent
- external archives: 0
- `node_modules`: 0
- `.next`: 0

This was a Phase 1 **BLOCK** because the release artifact could not reproduce the documented application.

## Reconciliation Patch

`scripts/build_release_zip.py` now includes:

- `apps`
- `backend`
- `requirements-api.txt`

It explicitly excludes:

- `node_modules`
- `.next`
- `.turbo`
- `build`
- `coverage`
- external archives and extracted references
- `.env`, secrets, cache, private data, local stores, and model artifacts

Regression coverage was added in `tests/test_phase5f_release_includes_web_backend.py`.

## Verified Release

Artifact:

`dist/global_market_terminal_20260619T134443Z.zip`

| Check | Result |
|---|---:|
| Selected source files | 1,266 |
| ZIP entries including manifest | 1,267 |
| `apps/web/package.json` | present |
| `apps/web/src/app/page.tsx` | present |
| `backend/api/app.py` | present |
| `requirements-api.txt` | present |
| `node_modules` | absent |
| `.next` | absent |
| `external` | absent |
| real `.env` | absent |
| Phase 5F external inventory CSV | absent from release, retained in repository audit artifacts |

## Release Verdict

**PASS for source release composition.** This does not mean the B2C product is complete. It means the documented architecture is now represented by the distributable source ZIP and the release hygiene boundary remains intact.

## Required Next Release Gates

1. Add a clean install test from the ZIP in a temporary directory.
2. Add documented commands for Streamlit lab, optional API, and web product.
3. Add a production deployment manifest only after environment and hosting choices are approved.
4. Keep fixture export deterministic and exclude all user-specific research memory.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
