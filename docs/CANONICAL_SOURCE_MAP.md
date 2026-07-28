# Canonical Source Map

This file records the ownership boundaries recovered before Phase 8 work.

## goal1

goal1 owns the Global Heatmaps, `market_data`, `global_markets`, and static universe baseline.

Required source areas:

- `lib/market_data.py`
- `lib/global_markets.py`
- `lib/heatmaps.py`
- `pages/7_Global_Heatmaps.py`
- `static/index_constituents/sp500.csv`
- `static/index_constituents/nasdaq100.csv`
- `static/index_constituents/korea_watchlist.csv`

## Phase4

Phase4 owns Crypto Intelligence, `DataResult`, cache infrastructure, crypto market data wrappers, crypto scenario logic, and crypto tests baseline.

Required source areas:

- `lib/data_status.py`
- `lib/cache.py`
- `lib/crypto_prices.py`
- `lib/crypto_derivatives.py`
- `lib/crypto_onchain.py`
- `lib/crypto_scenarios.py`
- `pages/8_Crypto_Intelligence.py`
- `tests/test_crypto_derivatives.py`
- `tests/test_crypto_onchain.py`
- `tests/test_crypto_scenarios.py`

## goal3

goal3 owns Equity, Energy, Geopolitical Risk, Scenario Lab, and Risk Lab additions.

Required source areas:

- `lib/equity_breadth.py`
- `lib/equity_scenarios.py`
- `lib/energy_data.py`
- `lib/oil_flows.py`
- `lib/geopolitical_news.py`
- `lib/worldmonitor_adapter.py`
- `lib/risk.py`
- `lib/stress_tests.py`
- `lib/scenario_engine.py`
- `pages/9_Energy_Geopolitics.py`
- `pages/10_Scenario_Lab.py`
- `pages/11_Risk_Lab.py`

Future `/goal` work must preserve these boundaries unless a later phase explicitly migrates code with tests and documentation.
