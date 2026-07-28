# Phase 5N Test Report

Updated: 2026-06-22

## Python

- Collected: 786 tests across 425 test files.
- Focused Phase 5N/API/Phase 5M regression slice: 36 passed.
- Full `python -m pytest -q -x`: passed.
- `python -m compileall -q app.py lib pages scripts tests backend`: passed.
- `python scripts/run_smoke_tests.py`: passed, including `lib.symbol_workstation`, `lib.symbol_intelligence`, and `lib.api_contracts`.
- Existing warnings retained: one FastAPI TestClient/httpx2 deprecation and two cointegration collinearity warnings.

## Web

- 25 deterministic API fixtures validated.
- ESLint passed.
- Next.js 16.2.9 production build passed.
- Runtime API success/fallback smoke passed for market and symbol routes.
- Chrome Phase 5N visual QA passed.
- npm high-severity audit: zero vulnerabilities.

## Runtime Evidence

Final provider probes showed AAPL 298.01 USD with latest closed-session timestamp, BTCUSDT near the user's observed 64.2k level with a current one-hour observation, source-backed equity/ETF financial availability, strict symbol-title news, public Binance derivatives rows, and 64/121-point comparison overlaps. Values remain time-dependent and are not hard-coded.

