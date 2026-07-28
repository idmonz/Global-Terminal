# Phase 5N Product And Quant Contract

## User Journey

The user searches a supported symbol, opens its canonical workstation, sees the latest verified market observation with a separate retrieval timestamp, switches line/candlestick views, enables bounded analysis panels, compares one supported symbol, inspects exact-match news and asset-appropriate context, and can refresh or return through the same URL.

Canonical route:

```text
/?view=asset&symbol=<SAFE_SYMBOL>&assetClass=<equity|etf|crypto>&interval=<SUPPORTED>&range=<SUPPORTED>&surface=<overview|chart|financials|news|sources>&panels=<BOUNDED_SET>&chartType=<line|candlestick>&compare=<SAFE_SYMBOL_OR_EMPTY>&mode=<fixture|cache|live-if-available>
```

## Time Truth

- `retrieved_at`: when the provider response was obtained.
- `market_data_as_of`: timestamp of the latest usable OHLCV observation.
- `observation_age_seconds`: age of that observation at contract build time.
- `market_data_status`: `intraday-current`, `latest-session`, `delayed-observation`, `stale-cache`, `fixture`, or `unavailable`.
- Equity daily history is not called real-time merely because it was freshly retrieved.
- Fixture values are synthetic and never compared with current-market expectations.

## Technical Formulas

- SMA: arithmetic rolling mean, windows 20 and 50.
- EMA: exponentially weighted mean with `adjust=False`, spans 20 and 50.
- RSI: 14-observation rolling average gain/loss implementation already used by `lib.technical_analysis`.
- MACD: EMA(12) minus EMA(26), signal EMA(9), histogram difference.
- Realized volatility: rolling standard deviation of returns over 20 observations, annualized by declared interval factor.
- Drawdown: close divided by running maximum minus one.
- Comparison: timestamp inner join and rebased total return from the first overlapping close; overlap count is explicit.

No missing price is forward-filled across unsupported dates. A panel is unavailable when its minimum observation count is not met.

## Asset-Specific Context

- Equity: public delayed ratios/statements availability plus SEC identity/filing availability when the configured user agent and public mapping succeed.
- ETF: fund profile/availability only; company statements are not shown.
- Crypto: mark, index, basis, funding, and open interest remain distinct public futures observations.
- News: title/summary must match a bounded canonical symbol alias or meaningful identity token. Broad headlines remain excluded.

All output is read-only research information and not investment advice or execution guidance.

