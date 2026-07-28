# Data Source Limitations

## General

- Free feeds can be delayed, rate-limited, incomplete, or unavailable.
- Missing values are surfaced as data gaps.
- Estimated and proxy fields are labeled.
- No fake data is presented as real.

## AI

- AI providers are optional.
- The rule-based fallback is deterministic and requires no key.
- AI text is neutralized for compliance before display.

## Market Data

- yfinance coverage varies by ticker, exchange, and asset class.
- Static universes are seeds and not guaranteed complete index membership.
- Crypto public endpoints can be rate-limited.

## Energy And Geopolitics

- EIA requires an optional key for richer fundamentals.
- News feeds can duplicate articles or omit precise locations.
- WorldMonitor integration is optional.
- AIS/live vessel flow is unavailable unless a provider is added later.

## Options

- yfinance option chains can be unavailable or delayed.
- Gamma exposure is an estimate/proxy and not dealer-confirmed GEX.
