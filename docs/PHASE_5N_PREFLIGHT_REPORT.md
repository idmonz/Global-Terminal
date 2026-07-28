# Phase 5N Preflight Report

Updated: 2026-06-22

## Verdict

The Phase 5M baseline is internally consistent and Phase 5N may proceed. The durable benchmark-parity goal remains active.

## Baseline Gates

- Python compileall: passed.
- Repository smoke imports: passed.
- Full `pytest -q -x`: passed; existing FastAPI/httpx2 deprecation and two cointegration collinearity warnings remain.
- Web fixture/runtime-boundary checks: passed; 25 fixtures validated.
- ESLint: passed.
- Next.js 16.2.9 production build: passed.
- npm high-severity audit: zero vulnerabilities.
- Baseline release: `dist/global_market_terminal_20260622T075203Z.zip`, 1,386 entries including the manifest.

## Reproduced Product Gap

Direct runtime probes returned:

| Symbol | Observation | Last market row | Retrieval state |
| --- | ---: | --- | --- |
| AAPL | 298.01 USD | 2026-06-18 daily close | live provider retrieval |
| MSFT | 379.40 USD | 2026-06-18 daily close | live provider retrieval |
| SPY | 746.74 USD | 2026-06-18 daily close | live provider retrieval |
| BTCUSDT | 64,173.70 USDT | 2026-06-22 07:00 UTC | live provider retrieval |
| ETHUSDT | 1,745.55 USDT | 2026-06-22 07:00 UTC | live provider retrieval |

The provider values match the user's stated AAPL and BTCUSDT observations closely. The visible stale-value defect is therefore primarily a product-routing and truth-label problem: asset routes default to `cache`, while retrieval time and last-observation time are not distinguished. A successful current fetch can also carry the latest closed equity session rather than an intraday quote.

## Phase Acceptance Focus

1. Asset routes default to `live-if-available`; fixture and cache remain explicit URL choices.
2. Retrieval time, last market observation, observation age, and market-session caveat are separate fields.
3. Price/volume/candlestick, technical, comparison, financial/news, and crypto derivatives panels remain symbol-scoped.
4. The desktop asset route gives the chart materially more width and proves it with inspected 1600x1000 captures.
5. Provider failure never substitutes fixture values inside a requested live response.

## Browser Baseline

The in-app Browser could not initialize because the session omitted its required sandbox metadata. Per the repository visual-QA skill, Phase 5N will use installed production Chrome with `playwright-core`; failed or missing captures will not be reported as passes.

