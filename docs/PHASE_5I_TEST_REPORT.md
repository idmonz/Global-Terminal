# Phase 5I Test Report

Updated: 2026-06-20

## Focused Tests

- `tests/test_phase5i_market_map_screener.py`: 7 passed.
- Phase 5I plus API fixture/backend/contract and prior market-workstation regression slice: passed.
- Provider normalization, provenance, missing-rank eligibility, deterministic fixture safety, sector/rank/scatter payloads, TTL/single-fetch behavior, stale fallback, route wiring, and web contract markers are covered.

## Defect Found By Full Regression

The first final full-suite run found one secret-scan false positive: the public route description contained the text `risk-return`, whose substring `sk-` matched an intentionally conservative API-key scan. The description was changed to `risk versus return`, fixtures were regenerated, the exact failing test passed, and the full suite then passed at 100%.

## Repository Gates

- `python -m compileall -q app.py lib pages scripts tests backend`: passed.
- `python scripts/run_smoke_tests.py`: passed.
- Full `python -m pytest -q -x`: passed at 100% after the false-positive correction.
- `python scripts/export_api_fixtures.py`: passed, 21 fixtures.
- `npm.cmd --prefix apps/web test`: passed, 21 `phase_2b.v1` fixtures and runtime UI markers.
- `npm.cmd --prefix apps/web run lint`: passed.
- `npm.cmd --prefix apps/web run build`: passed on Next.js 16.2.9.
- `npm.cmd --prefix apps/web run test:runtime-api`: passed success and fallback routes.
- `npm.cmd --prefix apps/web audit --audit-level=high`: 0 vulnerabilities.
- `npm.cmd --prefix apps/web run visual:phase5i`: passed desktop/mobile/fallback readiness and URL assertions.

## Visual Assertions

- desktop: 60 rows, 60 tiles, 60 table rows, 50 scatter points;
- mobile selected sector: 5 rows/tiles/table/scatter points;
- fixture: 30 rows/tiles/table/scatter points;
- browser console errors: 0.

## Warnings

- Existing cointegration collinearity warnings remain.
- FastAPI TestClient reports a Starlette deprecation warning about future `httpx2`; routes still pass.
