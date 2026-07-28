# Goal 12B Spec

Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions.

Goal 12B upgrades the Goal 12A research-only options calculator into a local options-chain, volatility-surface, option-book, and quant-diagnostics workstation.

## Scope

1. Supplied option-chain CSV ingestion with aliases for symbol/root/underlying, expiry, strike, option type, bid, ask, mark/last/mid, underlying price, timestamp, source, provider, OI/volume, supplied IV, and Greeks.
2. Chain quality and freshness labeling using user-supplied timestamps and sources.
3. Bid/ask/mid implied-volatility diagnostics using the existing deterministic IV solver.
4. Volatility surface snapshots from supplied rows only.
5. Smile, skew, and term-structure tables.
6. Calendar, diagonal, butterfly, iron-condor, ratio-spread, and custom multi-leg payoff templates.
7. Option book risk aggregation from supplied local positions only.
8. Contract-scaled Greek units.
9. Lightweight deterministic quant diagnostics for supplied time series.
10. Local report and attachment payloads.

## Non-Goals

- No live market-data fetch by default.
- No execution, approval, route, or autonomous decision surface.
- No heavy ML runtime, model weights, TensorFlow, Torch, HuggingFace, TensorTrade, Kronos, or QuantDinger dependency.
- No external source-code copy.
