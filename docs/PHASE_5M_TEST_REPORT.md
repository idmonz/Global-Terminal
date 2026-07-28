# Phase 5M Test Report

Updated: 2026-06-22

## Focused Coverage

Phase 5M tests cover:

- registry coverage and asset-class counts;
- aliases, exact resolution, ranking, limits, and input bounds;
- independent deterministic fixtures and cross-symbol leakage;
- interval/range capability rejection;
- symbol/interval/range cache partitioning;
- cache-miss, stale timestamp, and provider failure semantics;
- API routes, fixture export, and backend getters;
- Market Map, watchlist, and Research Memory route generation;
- release inclusion and private/external exclusions.

`tests/test_phase5m_symbol_workstation.py` passed 9 focused tests before the full regression run.

## Runtime Smoke

Live local evidence:

- MSFT: yfinance, 64 rows, every row symbol `MSFT`;
- SPY: yfinance, 64 rows, every row symbol `SPY`;
- ETHUSDT: Binance USD-M Futures, 121 rows, every row symbol `ETHUSDT`;
- unknown symbol: `unknown-symbol`;
- unsupported interval: `unsupported-interval`;
- empty cache: `cache-miss`.

The web self-contained runtime smoke now covers both market intelligence and MSFT symbol-workstation API success/fallback paths.

## Gates

- Python compileall: passed.
- Python smoke imports: passed.
- focused Phase 5M/API tests: passed.
- 25 deterministic API fixtures: passed.
- ESLint: passed with zero warnings.
- Next.js 16.2.9 production build: passed.
- runtime API success/fallback smoke: passed.
- production Chrome visual/interaction harness: passed.
- npm audit high: zero vulnerabilities.

## Final Full Suite

`python -m pytest -q -x` passed all 775 collected tests.

Warnings were limited to:

- one existing FastAPI `TestClient`/httpx2 deprecation warning;
- two existing cointegration collinearity warnings.

Focused Phase 5M symbol/release tests passed 10/10 after the reports were added.
