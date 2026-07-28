# Financial Terminal Guide

The Financial Terminal is implemented by `lib/financial_terminal.py`, `lib/financial_charts.py`, enhancements in `lib/fundamentals.py`, and `pages/15_Financial_Terminal.py`.

## Data Sources

Primary free-mode source is yfinance. Optional providers can be added later through configured API keys, but the current page does not require them.

## Tabs

- Overview
- Statements
- Statistics
- Valuation
- Earnings
- Revenue
- Cash Flow
- Balance Sheet
- Filings / Ownership
- Peers
- Data Status

## Missing Data Rules

- Reported-vs-estimate charts render only when provider estimate fields exist.
- Segment and geographic revenue panels stay empty unless real provider data exists.
- Ratios are source-derived or derived from reported statements.
- Unavailable fields are shown as data gaps in the availability matrix.

The page does not estimate fair value or produce directional trade directives.
## Goal 8 OpenBB Source Modes

- Financial Terminal supports Auto, Native only, OpenBB preferred, and OpenBB only.
- OpenBB can enrich profile, price history, statements, ratios, metrics, estimates, filings, peers, and ownership where provider access exists.
- Native yfinance/fundamentals are not removed.
- Estimates, segment revenue, and geographic revenue are not fabricated; unavailable fields stay visible as data gaps.

## Goal 9 Unified Endpoint Status

Financial Terminal now exposes unified endpoint status for price history, income, balance, cash flow, ratios, and metrics.

The page shows provider, source, freshness, native/OpenBB/fallback flags, source confidence, and data gaps. Estimates, segment revenue, geography revenue, and transcripts remain unavailable unless provider-supplied.
# Goal 10 Update

Financial Terminal is addressable through the command UX with ticker/function patterns such as `AAPL FA`, `AAPL KEY`, `AAPL FIL`, and `AAPL OMON`. SEC EDGAR integration requires `SEC_USER_AGENT` and remains source-labeled.
