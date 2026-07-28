# Phase 5J API, Data, And Model Contract

Updated: 2026-06-21

## Payload

- payload type: `options_quant`;
- workspace version target: `options_quant.v2`;
- route: `GET /api/options-quant`;
- query: `symbol`, optional `expiry`, and `include_runtime`;
- fixture: `static/api-fixtures/options-quant.json`.

## Collections

- `expiries`, `chain_rows`, and `rejected_rows`;
- `iv_smile`, `iv_term_structure`, and gated `surface_points`;
- `greeks_rows` and `greek_units`;
- `gamma_exposure_by_strike`;
- `scenario_rows`;
- `quality`, `assumptions`, `source_register`, `unavailable_sources`, `readiness`, and `summary`.

## Provider Boundary

yfinance supplies delayed public equity-option rows. `fetched_at` records retrieval time. `last_trade_at` records the provider's last trade timestamp and must not be labeled quote time. Contract multiplier 100, American exercise style, risk-free rate, and dividend yield are explicit model assumptions unless supplied by a verified provider.

## Quality Rules

Reject:

- missing/invalid contract identity, side, expiry, strike, underlying, bid, or ask;
- non-positive strike, underlying, or multiplier;
- negative bid/ask/last/volume/open interest/IV;
- bid greater than ask;
- expired contracts;
- duplicate provider/symbol/expiry/strike/side identity.

Caveat but preserve:

- zero bid and ask;
- missing volume, open interest, or IV;
- last trade older than the documented threshold;
- wide spread;
- assumed multiplier, exercise style, rates, or dividend yield.

Missing values remain null.

## Models

- Equity options: Black-Scholes research approximation.
- Provider IV is preserved separately from any solved IV.
- Greeks expose per-unit and contract-scaled units.
- Scenario rows use bounded spot/volatility shocks and the selected contract's current time to expiry.
- GEX requires gamma, OI, multiplier, and spot. Calls use +1 and puts -1 only as an explicit dealer-sign convention.
- Surface readiness requires at least two expiries and at least three valid strikes per included expiry; sparse data stays unavailable.

All calculations include model, inputs, units, timestamp alignment, solver/quality status, assumptions, caveat, and `not_financial_advice=true`.
