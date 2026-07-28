# Phase 4 Crypto Intelligence Report

## Files Created Or Modified

- `pages/8_Crypto_Intelligence.py`
- `lib/crypto_derivatives.py`
- `lib/crypto_prices.py`
- `lib/crypto_onchain.py`
- `lib/crypto_scenarios.py`
- `lib/claude_analyst.py`
- `lib/compliance.py`
- `scripts/run_smoke_tests.py`
- `tests/test_crypto_derivatives.py`
- `tests/test_crypto_onchain.py`
- `tests/test_crypto_scenarios.py`
- `pytest.ini`
- `docs/DATA_SOURCES.md`
- `docs/IMPLEMENTATION_CHECKLIST.md`
- `docs/CHANGELOG.md`

## Endpoints Implemented

- Binance USD-M Futures: exchange info, klines, open interest, open interest history, funding rate, premium index, taker buy/sell ratio, global long/short ratio, top trader account ratio, top trader position ratio, recent trades.
- CoinGecko: public market table and overview metrics.
- DefiLlama: chain TVL, protocols, stablecoins, stablecoins by chain, DEX volume, fees.

## Free-Mode Capabilities

- BTCUSDT/ETHUSDT/SOLUSDT/BNBUSDT/XRPUSDT/DOGEUSDT Binance futures diagnostics.
- OI, funding, basis, taker flow, and long/short ratio tables and charts.
- CoinGecko top market table.
- DefiLlama on-chain and stablecoin sections.
- Estimated liquidation pressure map with caveat.
- Neutral scenario matrix.

## Optional Provider Limits

CoinGlass, Glassnode, CryptoQuant, Santiment, Kaiko, CoinMarketCap, and CoinAPI are not required. They appear as optional paid-provider data gaps in Phase 4.

## Liquidation Map Methodology

The map uses current price, ATR, recent swing highs/lows, support/resistance proxy, round levels, leverage bands, OI change, volume proxy, and funding context. Scores are normalized to 0-100 and labeled estimated. It is not official exchange liquidation data.

## Compliance Notes

The compliance scanner preserves descriptive market-structure terms such as long/short ratio and taker buy/sell ratio while continuing to block action-oriented recommendation language.

## Known Limitations

- Binance free public REST data is single-exchange and can be rate-limited or geofenced.
- Live forceOrder websocket liquidations are deferred.
- DefiLlama endpoint schemas may change; sections degrade independently.
- CoinGecko public endpoints are rate-limited.

## Tests Run

- `python scripts/run_smoke_tests.py` passed.
- `python -m pytest -q` passed with 19 tests.
- Bare `pytest -q` was attempted, but this PowerShell environment does not have the `pytest` launcher on PATH. The committed `pytest.ini` provides the requested Python path configuration when pytest is invoked.

## Next Phase

Phase 5 should add equity breadth, technical diagnostics, options-chain proxies, and neutral stock/index scenario engines.
