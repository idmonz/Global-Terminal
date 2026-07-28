# Return Forecast Caveats

`lib/return_forecast.py` implements historical mean, EWMA, momentum-adjusted, factor-model fallback, bootstrap, Monte Carlo, and regime-conditioned estimates.

Every forecast includes:

> This is a model estimate based on historical/proxy data, not a prediction or investment advice.

Forward distributions are sensitive to lookback windows, sampled returns, volatility assumptions, factor proxies, and regime labels. They do not guarantee outcomes.
