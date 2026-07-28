# Phase 5M Preflight Report

Date: 2026-06-22

## Verdict

The repository baseline is green, but universal symbol coverage is absent. The commercial web route accepts only `AAPL` and `BTCUSDT`; `MSFT`, `SPY`, and `ETHUSDT` render the explicit unknown-symbol state. The optional API can accept another symbol string, but existing deterministic equity/crypto fixtures were authored around AAPL/BTC and are not a safe universal fallback. Phase 5M therefore requires a new symbol-master and symbol-workstation boundary, not only a larger frontend allow-list.

## Baseline Evidence

- Python compile: passed.
- Import smoke: passed, including Phase 5L Research Memory.
- Full Python regression: 765 tests collected and passed.
- Warnings: one FastAPI/TestClient deprecation warning and two existing cointegration collinearity warnings.
- Fixture validation: 23 `phase_2b.v1` fixtures passed.
- Web lint: passed.
- Next.js 16.2.9 production build: passed.
- npm audit at high severity: zero vulnerabilities.
- Fixture export: passed, 23 fixtures.
- Release build: passed.
- Baseline release: `dist/global_market_terminal_20260622T024546Z.zip`.
- Release entries: 1,368 including manifest.
- Release boundary: web, backend, and manifest present; `.env`, private databases, external archives, `node_modules`, and `.next` absent.

## Observed Product Gap

HTTP checks against the running product returned 200 responses, but all three routes displayed `No verified workspace`:

- `MSFT` equity
- `SPY` equity/ETF
- `ETHUSDT` crypto

The current top-bar search is a two-row datalist. The Market Map exposes sixty equity rows but only AAPL has a verified workstation action. Research Memory watchlist symbols are not workstation links.

## Acceptance Boundary

Phase 5M must:

1. expose at least 50 equity/ETF identities and 20 crypto identities;
2. resolve exact symbols and bounded ranked search without provider or shell injection;
3. provide symbol-specific fixture, cache, live-if-available, stale, failure, and unsupported states;
4. key history caches by symbol, interval, and range;
5. prevent AAPL/BTC fixture fields from appearing under another symbol;
6. provide canonical interval/range/surface URL state;
7. connect Market Map and Research Memory watchlists to the resolved asset route;
8. preserve all Phase 5G through Phase 5L behavior and release exclusions.

