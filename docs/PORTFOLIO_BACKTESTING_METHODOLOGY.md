# Portfolio Backtesting Methodology

## Engine

`lib/portfolio_backtester.py` aligns price histories, computes asset returns, applies portfolio weights, simulates optional rebalancing, subtracts transaction/slippage estimates, and reports performance metrics.

## Metrics

The engine reports cumulative return, CAGR, annualized volatility, Sharpe, Sortino, Calmar, max drawdown, VaR, CVaR, benchmark beta, regression alpha estimate, tracking error, information ratio, monthly win statistics, turnover, and transaction cost estimate.

## Missing Data

Missing non-cash assets are flagged and excluded from return math. They are not treated as zero-return assets. Cash rows can be represented explicitly with `CASH`.

## Limitations

Backtests use historical/proxy data, simple rebalancing assumptions, and simplified transaction costs. They do not model taxes, borrow, market impact, intraday execution, path-dependent liquidity, or future conditions.
