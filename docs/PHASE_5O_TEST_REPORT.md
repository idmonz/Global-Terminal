# Phase 5O Test Report

Updated: 2026-06-22

## Final Results

- collected Python tests: 795;
- full `python -m pytest -q`: pass;
- Python compileall: pass;
- import smoke: pass;
- focused Phase 5I/5O compatibility tests: pass;
- saved-screen FastAPI CRUD tests: pass;
- fixture export: 25 valid `phase_2b.v1` fixtures;
- web fixture/runtime markers: pass;
- ESLint: pass;
- Next.js production build and TypeScript: pass;
- runtime API smoke: pass;
- npm high-severity audit: 0 vulnerabilities;
- Phase 5O browser QA: pass;
- release hygiene regression slice: pass.

## Defects Found By Gates

1. `risk-adjusted` contained the secret-scan substring `sk-`. The public model ID became `risk_adjusted`.
2. An SVG title caused React hydration mismatch. Accessible `aria-label` text replaced it.
3. Phase 5O initially overwrote Phase 5I legacy rank eligibility. Legacy fields are now preserved and new models remain additive.
4. The next-goal document contained an absolute user path. It now uses repository-relative context.
5. The external audit script failed on an unresolved relative input path. The final audit used a resolved absolute input; the script behavior is recorded for later hardening.

## Retained Warnings

- existing Starlette/httpx2 TestClient deprecation warning;
- two existing cointegration collinearity warnings.

No warning is caused by the Phase 5O discovery or saved-screen calculations.
