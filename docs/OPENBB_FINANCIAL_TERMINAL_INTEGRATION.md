# OpenBB Financial Terminal Integration

`lib/financial_terminal.py` now supports source modes:

- Auto
- Native only
- OpenBB preferred
- OpenBB only

OpenBB can enrich profile, price history, statements, ratios, metrics, estimates, segment/geographic revenue, filings, peers, and ownership when available.

Native yfinance/fundamentals remain intact. Estimates, segment revenue, and geography revenue are displayed only when supplied by a provider. Missing fields remain explicit data gaps.
