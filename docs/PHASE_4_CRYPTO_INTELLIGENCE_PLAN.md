# Phase 4 Crypto Intelligence Plan

## Current Placeholder State

- `pages/8_Crypto_Intelligence.py` renders a crypto heatmap table and a Phase 4 placeholder note.
- `lib/crypto_prices.py` delegates to the Phase 3 heatmap helper only.
- `lib/crypto_derivatives.py` and `lib/crypto_onchain.py` return planned/unavailable statuses.
- `lib/crypto_scenarios.py` returns a minimal three-row data-gap scenario list.
- `scripts/run_smoke_tests.py` does not yet import crypto Phase 4 modules.
- No crypto tests exist yet.

## Phase 4 Files To Modify

- `pages/8_Crypto_Intelligence.py`
- `lib/crypto_prices.py`
- `lib/crypto_derivatives.py`
- `lib/crypto_onchain.py`
- `lib/crypto_scenarios.py`
- `lib/claude_analyst.py`
- `scripts/run_smoke_tests.py`
- `tests/test_crypto_derivatives.py`
- `tests/test_crypto_onchain.py`
- `tests/test_crypto_scenarios.py`
- `docs/DATA_SOURCES.md`
- `docs/IMPLEMENTATION_CHECKLIST.md`
- `docs/CHANGELOG.md`
- `docs/PHASE_4_CRYPTO_INTELLIGENCE_REPORT.md`

## APIs To Implement

Free-mode sources:

- Binance USD-M Futures public API:
  - `/fapi/v1/exchangeInfo`
  - `/fapi/v1/klines`
  - `/fapi/v1/openInterest`
  - `/futures/data/openInterestHist`
  - `/fapi/v1/fundingRate`
  - `/fapi/v1/premiumIndex`
  - `/futures/data/takerlongshortRatio`
  - `/futures/data/globalLongShortAccountRatio`
  - `/futures/data/topLongShortAccountRatio`
  - `/futures/data/topLongShortPositionRatio`
  - `/fapi/v1/trades`
- CoinGecko public market API:
  - `/api/v3/coins/markets`
  - `/api/v3/simple/price`
- DefiLlama public API:
  - `/v2/chains`
  - `/protocols`
  - `/stablecoins`
  - `/stablecoins/chains`
  - `/overview/dexs`
  - `/overview/fees`

Optional paid providers remain status-only stubs for Phase 4.

## Test Strategy

- Keep tests offline by monkeypatching network calls and request wrappers.
- Validate Binance symbol normalization and normalized DataFrame schemas.
- Validate `DataResult` error behavior for malformed or unavailable provider responses.
- Validate the estimated liquidation pressure map required columns and 0-100 pressure scores.
- Validate the scenario matrix has four neutral scenarios with no forbidden recommendation language.
- Validate crypto market-structure terms such as `long/short ratio` remain allowed in compliance checks.
- Run both `python scripts/run_smoke_tests.py` and `pytest -q`.

## Compliance Constraints

- No personalized financial advice.
- No action labels such as buy/sell/hold or direct trade instructions.
- Required market-structure terms are allowed when descriptive: long/short ratio, long liquidation, short liquidation, long exposure, short exposure.
- All scenario output uses neutral labels: evidence weight, watch-points, invalidation level, data gaps, catalysts, and confidence caveat.
- The page footer uses the standard disclosure.

## Known Free-Data Limitations

- Binance public REST endpoints are single-exchange and may be rate-limited or geofenced.
- Binance liquidation websocket streams are deferred in this phase; the REST page labels that limitation.
- CoinGecko public endpoints can rate-limit and do not cover institutional-grade intraday market structure.
- DefiLlama endpoint schemas can evolve; each on-chain section must degrade independently.
- The liquidation pressure map is an estimate from price, volatility, pivots, open interest, volume proxy, and funding context. It is not official exchange liquidation data.
