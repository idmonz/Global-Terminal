# Options Gamma Proxy Caveats

`lib/options_flow.py` uses yfinance option chains when available.

## Important Caveat

"Estimated gamma exposure proxy, not dealer-confirmed GEX."

True dealer gamma exposure requires assumptions about dealer positioning, volatility surfaces, contract multipliers, hedging behavior, and trade direction that are not observable from free option-chain data.

## Implemented Proxies

- Put/call open interest ratio.
- Put/call volume ratio.
- Max pain proxy from open interest.
- Largest OI strikes.
- Expiry concentration.
- Gamma exposure proxy by strike.

## Gamma Approximation

- Uses Black-Scholes gamma when implied volatility, spot, strike, and expiry are available.
- Falls back to OI-weighted strike proximity when inputs are missing.
- Separates call-side and put-side proxy pressure.

The output is context, not a trading signal.
