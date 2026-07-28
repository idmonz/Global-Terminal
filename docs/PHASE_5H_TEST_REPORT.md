# Phase 5H Test Report

Updated: 2026-06-20

## Focused Tests

- Phase 5H map, War Room map, fusion, API contract, backend route, and War Room tests: 40 passed.
- Optional FastAPI route smoke now runs rather than skips after installing FastAPI.
- DataFrame-direct news payload regression added.
- OpenSky configured-but-failed behavior remains unavailable/error-labeled.

## Repository Gates

- `python -m compileall -q app.py lib pages scripts tests backend`: passed.
- `python scripts/run_smoke_tests.py`: passed.
- Full `pytest -q -x`: passed at 100% on the final worktree. Existing warnings only.
- `npm.cmd --prefix apps/web test`: passed, 20 fixtures.
- `npm.cmd --prefix apps/web run lint`: passed.
- `npm.cmd --prefix apps/web run build`: passed on Next.js 16.2.9.
- `npm.cmd --prefix apps/web run test:runtime-api`: passed success and fallback routes.
- `npm.cmd --prefix apps/web audit --audit-level=high`: 0 vulnerabilities.
- `npm.cmd --prefix apps/web run visual:phase5h`: passed ready/mobile/fallback assertions.

## Warnings

- Existing cointegration collinearity warnings remain.
- FastAPI TestClient reports a Starlette deprecation warning about future `httpx2`; it does not fail routes.

The final full suite was run in a background process to avoid the command transport time limit. `review_workspace/phase5h_visual/pytest-final.stdout.log` records the complete 100% pass.

