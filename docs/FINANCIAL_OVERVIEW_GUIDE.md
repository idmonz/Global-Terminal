# Financial Overview Guide

`lib/fundamentals.py` powers the Stock Analyzer financial tabs.

## Data Sources

- Primary free source: yfinance statements and info fields.
- Optional provider keys may be added later for FMP, Alpha Vantage, Polygon, or Finnhub.
- Missing statements are shown as data gaps.

## Metrics

- Income: revenue, gross profit, operating income, net income, EPS when available.
- Margins: gross, operating, net, and EBITDA margin when available.
- Cash flow: operating cash flow, capex, free cash flow, FCF margin path.
- Balance sheet: cash, debt, net debt, assets, liabilities, equity.
- Ratios: trailing P/E, forward P/E, P/S, P/B, EV/EBITDA, debt/equity, ROE, ROA, current ratio.

## Caveats

- yfinance fields can vary by ticker and exchange.
- Statement frequency and fiscal calendars may differ.
- Missing data is not filled with fabricated values.
