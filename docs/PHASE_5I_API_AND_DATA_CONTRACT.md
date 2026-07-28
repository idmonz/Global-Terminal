# Phase 5I API And Data Contract

Updated: 2026-06-20

## Payload

- payload type: `market_map_screener`;
- workspace version: `market_map_screener.v1`;
- route: `GET /api/market-map-screener`;
- query: `include_runtime`, `period`;
- fixture: `static/api-fixtures/market-map-screener.json`.

## Collections

- `instruments` / `heatmap_tiles`;
- `ranked_rows`;
- `scatter_points`;
- `sector_summaries`;
- `filter_options`;
- `source_register`;
- `unavailable_sources`;
- `readiness` and `summary`.

## Instrument Fields

Every row includes symbol/name, asset class, sector/industry, region/exchange, market-cap or fixture size metric, price and return windows, volatility/drawdown/RSI where available, rank eligibility/score/rank, provider/source URL/fetched time/freshness/source status/confidence, taxonomy status, caveat, data gap, and `not_financial_advice=true`.

## Data Separation

- yfinance supplies delayed public market history.
- `static/index_constituents/sp500.csv` supplies local taxonomy and approximate market-cap metadata.
- Market observations and taxonomy have separate status fields.
- Static taxonomy is not claimed as current index membership.
- Missing values are not imputed to zero for ranking.

## Cache

A module-level lock provides single-flight behavior. Fresh rows use a 10-minute TTL. A failed refresh may retain a labeled stale copy for up to one hour. Tests cover fresh -> cached and fresh -> failed refresh -> stale transitions.

## Deterministic Fixture

Fixture rows reuse the existing clean-room market heatmap fixture, add deterministic synthetic volatility/rank inputs, use `example.test` source URLs, and remain `source_status=fixture`. They are regression/demo data only.

