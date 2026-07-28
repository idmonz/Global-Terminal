# Phase 5X Implementation Report

Updated: 2026-06-30

## Verdict

Phase 5X improved real provider breadth and controlled online/offline QA. It did not complete the durable benchmark-parity goal.

## What Changed

- Added `lib/equity_provider_breadth.py`.
- Wired Alpha Vantage and Finnhub into AAPL/equity symbol intelligence as optional free-first provider breadth.
- Added provider rows to the Symbol Workstation financial context, exact-news context and source register.
- Added an AAPL Financials `Free provider breadth` panel in the Next.js web product.
- Added `apps/web/scripts/capture-phase5x.mjs` and `npm run visual:phase5x`.
- Updated `.env.example` and `docs/FREE_API_KEY_CHECKLIST.md`.
- Refreshed the external archive inventory.

## Provider Behavior

`.env` was checked without printing secret values:

- `ALPHAVANTAGE_API_KEY`: present.
- `FINNHUB_API_KEY`: present.
- `SEC_USER_AGENT`: present.
- `GEMINI_API_KEY`: present.
- OpenSky OAuth variables: not configured in this repo state.

Live AAPL smoke on 2026-06-30:

- Alpha Vantage overview: `live/fresh`, 16 normalized profile/fundamental fields.
- Finnhub profile: `live/fresh`, 8 normalized company/profile fields.
- Alpha Vantage news: `live/fresh`, 8 rows.
- Finnhub company news: `live/fresh`, 8 rows.
- Symbol workstation merged exact-news rows: 11 rows after dedupe.

Cache behavior after the first live call:

- AAPL Financials visual QA showed cached Alpha/Finnhub rows with source times.
- Cached rows are labeled `cached`, not live.
- Missing keys return `missing-key`/`provider-required`.
- Rate-limit/provider errors return explicit non-live states and do not cache bad provider payloads.

## UI Result

AAPL Financials now shows:

- yfinance/SEC financial context.
- Alpha Vantage PE, revenue TTM and ROE.
- Finnhub market cap and industry.
- Provider status cards for Alpha Vantage and Finnhub.
- Caveats that free-tier data is supplemental and target-price fields are excluded.

AAPL News now includes source-backed company/ticker rows from Alpha Vantage/Finnhub when available.

## Clean-Room Notes

The implementation uses first-party provider code and official public API endpoints. External archives were used as behavior evidence only:

- OpenStock/worldmonitor showed Finnhub-like company profile/news behavior, but both are AGPL/reference-only for this product boundary.
- OpenBB showed provider-aware finance workspace behavior, but AGPL source was not copied.
- TradingView/OpenBB/Finnhub/Alpha Vantage product/API behavior informed the first-viewport source-aware financial panel.

No external source, screenshot, CSS, asset, dataset, target-price field, order action, or recommendation language was copied into the runtime product.

## Remaining Gaps

- The product is still not benchmark-grade.
- Earnings calendar, analyst estimates, ownership, SEC company facts, and full financial statement history need deeper source-backed treatment.
- War Map still lacks WorldMonitor/worldview-level layer richness, timeline interaction and live provider breadth.
- Market heatmap remains bounded rather than full-universe authoritative.
- Hosted auth, billing, sync, monitoring, alerts and CI/CD are still future work.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
