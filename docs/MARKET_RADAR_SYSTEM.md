# Market Radar System

## Module

`lib/market_radar.py`

## Purpose

Convert existing market, breadth, crypto, energy, and volatility payloads into normalized 0-100 radar components for compact terminal panels.

## Builders

- `build_cross_asset_radar()`
- `build_equity_breadth_radar()`
- `build_crypto_derivatives_radar()`
- `build_energy_risk_radar()`
- `build_volatility_radar()`
- `build_market_composite_score()`

## Labels

Neutral labels are used:

- Constructive backdrop
- Mixed evidence
- Deteriorating breadth
- Elevated volatility
- Crowding risk
- Liquidity pressure
- Data gap

## Caveats

- Scores are heuristic and not forecasts.
- A 0-100 score is a compact visualization scale, not an official risk rating.
- Missing provider data lowers confidence and is shown through source status or data-gap cards.
