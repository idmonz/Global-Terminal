# Phase 5K Test Report

Updated: 2026-06-21

## Focused Coverage

`tests/test_phase5k_portfolio_risk_workstation.py`: 8 passed.

Coverage includes:

- deterministic fictional demo usefulness and privacy labels;
- duplicate, non-positive and unsupported-FX holding rejection;
- complete-overlap return semantics and missing-symbol null handling;
- provider failure with no fabricated performance;
- TTL stale fallback with refresh cause;
- correlation sample counts and contribution reconciliation;
- JSON-safe API envelope and private-path scan;
- deterministic demo repeatability.

Phase 5K plus existing portfolio/API regression slice: 40 passed.

## Full Gates

- `python -m compileall -q app.py lib pages scripts tests backend`: passed.
- `python scripts/run_smoke_tests.py`: passed.
- `python -m pytest -q -x`: passed at 100%.
- `python scripts/export_api_fixtures.py`: passed, 22 fixtures.
- `npm.cmd --prefix apps/web test`: passed.
- `npm.cmd --prefix apps/web run lint`: passed.
- `npm.cmd --prefix apps/web run build`: passed on Next.js 16.2.9.
- `npm.cmd --prefix apps/web run test:runtime-api`: success and fallback passed.
- `npm.cmd --prefix apps/web audit --audit-level=high`: 0 vulnerabilities.
- `npm.cmd --prefix apps/web run visual:phase5k`: passed.

Warnings remain:

- FastAPI TestClient future Starlette/httpx2 transition.
- Existing deliberate cointegration collinearity warnings.

## Live Runtime Evidence

First yfinance composition:

- source status: `live/fresh`;
- holdings: 7/7 priced;
- non-cash history: 6/6;
- valuation/history coverage: 100% / 100%;
- complete daily observations: 249;
- correlation: six assets / 36 cells;
- factors: four public proxies;
- stress scenarios: nine;
- data gaps: zero;
- measured API composition: 4.66 seconds.

Immediate repeat:

- source status: `cached`;
- response time: 0.123 seconds;
- observations: 249.

