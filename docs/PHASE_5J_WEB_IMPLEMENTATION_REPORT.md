# Phase 5J Web Implementation Report

Updated: 2026-06-21

## Delivered Journey

`AAPL or Product Nav -> Options Quant -> expiry/type/moneyness -> chain -> IV/Greeks/exposure/scenario -> source and assumption inspection`

## Runtime

- New reusable builder: `lib/options_quant_workstation.py`.
- Existing free yfinance path supplies expiries and selected-plus-next-two chains.
- Five-minute TTL, module lock for single-flight behavior, and 30-minute stale fallback.
- Provider rows pass first-party identity, numeric, expiry, crossed-market, duplicate, and missing-field checks.
- Missing OI/volume/IV remain null and receive quality flags.
- Retrieval time, last-trade time, and unavailable quote time remain distinct.
- Existing project-native Greeks and scenario engines are reused.

## Contract

- `options_quant.v2` remains under the additive `phase_2b.v1` envelope.
- Existing `GET /api/options-quant` now accepts optional `expiry`.
- New collections: chain/rejected rows, IV smile/term/surface, Greeks, exposure, scenarios, quality, assumptions, readiness, sources, and unavailable states.
- Deterministic fixture contains 42 contracts across three expiries and 15 scenario states.
- Backward-compatible calculator/Greeks/scenario fields remain for prior diagnostics tests.

## Product UI

- Product-first `/?view=options-quant` route.
- Product navigation entry plus AAPL options-surface link.
- URL-backed symbol, expiry, surface, option type, moneyness, selected contract, compare expiries, and runtime mode.
- Dense calls/strike/puts table with clickable quotes.
- Source IV chart and term strip.
- Per-unit and contract-scaled Greeks table.
- Assumption-dependent gamma exposure chart.
- Bounded spot/volatility scenario matrix.
- Selected contract, quality, model assumptions, source rail, and research disclosure.
- Compact mobile header/navigation places chain context in the first viewport.

## Main Files

- `lib/options_quant_workstation.py`
- `lib/web_market_workstations.py`
- `lib/api_contracts.py`
- `backend/api/app.py`
- `apps/web/src/components/OptionsQuantWorkstation.tsx`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/src/lib/fixtures.ts`
- `apps/web/scripts/capture-phase5j.mjs`
- `tests/test_phase5j_options_quant_workstation.py`

## Honest Boundaries

- yfinance is unofficial delayed public data.
- Bid/ask quote timestamps are unavailable; last trade time is not relabeled.
- Black-Scholes is a European-model approximation and does not model American early exercise.
- Rate, dividend yield, multiplier, exercise style, and dealer sign are explicit assumptions.
- Gamma exposure is not observed dealer positioning.
- No order entry, broker integration, personalized recommendation, or execution control was added.
