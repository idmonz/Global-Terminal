# Portfolio Optimizer Caveats

`lib/portfolio_optimizer.py` implements equal weight, inverse volatility, min variance proxy, max Sharpe proxy, risk parity proxy, max diversification proxy, volatility targeting, and weight constraints.

Optimizers are research tools. They depend on historical returns, covariance estimates, constraints, and fallback behavior when optimization fails. The default mode is no-short and can cap per-asset weights.

Outputs are labeled research candidates, not advice.
