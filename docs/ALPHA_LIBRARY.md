# Alpha Library

`lib/alpha_library.py` provides neutral research signal families:

- Momentum: multi-horizon return with optional skip-last-month handling.
- Trend: moving-average, Donchian, and volatility-breakout proxies.
- Mean reversion: RSI, Bollinger z-score, and short-term reversal proxies.
- Low volatility: realized volatility, drawdown, and downside volatility ranks.
- Value and quality: optional fundamental proxy scores.
- Carry: bond, commodity, crypto funding, and dividend-yield proxy fields where supplied.
- Macro rotation: rates, USD, oil, gold, volatility, and breadth context.
- Crypto derivatives: funding, OI change, taker imbalance, long/short ratio, and liquidation-pressure estimate.
- News-aware: event severity, related assets, source count, and freshness context.

All signals use the schema `signal_name`, `family`, `asset`, `score`, `direction_label`, `evidence`, `data_gaps`, and `caveat`.
