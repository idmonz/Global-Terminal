# Phase 5M Visual QA Report

Updated: 2026-06-22

## Method

The in-app Browser bootstrap was unavailable because the current environment did not provide the required browser sandbox metadata. The repository-approved fallback used installed production Chrome with `playwright-core` against the production Next.js server and local FastAPI runtime.

The harness is `apps/web/scripts/capture-phase5m.mjs`.

## Automated Assertions

- exact requested symbol identity;
- no cross-symbol workstation text;
- nonzero chart points for ready charts;
- explicit fixture, cached, cache-miss, chart-fallback, and unknown states;
- canonical URL persistence;
- ranked search and MSFT client-side navigation;
- visible keyboard focus;
- no document overflow;
- zero console and page errors.

## Observed Evidence

| Surface | Result |
|---|---|
| AAPL fixture | 48 points, ready |
| MSFT live-if-available | cached yfinance, 64 points |
| MSFT cache | cached yfinance, 64 points |
| SPY ETF | cached yfinance, 64 points |
| BTCUSDT 1h/5d | cached Binance, 121 points |
| ETHUSDT 1h/5d | ready/cached Binance, 121 points |
| SUIUSDT cache | cache-miss, 0 points, explicit unavailable |
| NOTREAL | unknown-symbol, no substituted rows |
| forced chart fallback | explicit fallback, 0 rendered points |
| tablet 768x1024 | product width 724, document width 768 |
| mobile 390x844 | product width 359, document width 390 |

Search for `micro` ranked MSFT, MU, and AMD. Opening MSFT retained `interval=1d` and `range=3mo`. Browser console and page error counts were zero.

## Inspected Captures

- `review_workspace/phase5m_visual/msft-runtime-desktop.png`
- `review_workspace/phase5m_visual/btcusdt-crypto-desktop.png`
- `review_workspace/phase5m_visual/suiusdt-cache-miss-desktop.png`
- `review_workspace/phase5m_visual/unknown-symbol-desktop.png`
- `review_workspace/phase5m_visual/msft-runtime-tablet.png`
- `review_workspace/phase5m_visual/ethusdt-runtime-mobile.png`

All captures were personally inspected. Desktop density, source truth, chart hierarchy, and failure honesty are strong. Tablet and mobile have no horizontal document overflow. The compact mobile workspace rail remains intentionally secondary and scrollable; future design phases should continue reducing its prominence.

## Defects Found And Fixed

1. Unknown-symbol product state lacked the workstation state marker.
2. Intraday chart conversion collapsed hourly observations to duplicate daily timestamps.
3. Chart resize cleanup was made instance-local to avoid lifecycle ambiguity.

The final production-browser run passed after these corrections.
