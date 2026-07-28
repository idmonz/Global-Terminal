# Phase 6E Implementation Report

Updated: 2026-07-03

## Product Changes

- direct asset rendering now returns before `loadAllFixtures()`;
- a 9-symbol compact offline summary catalog replaces the 20 MB full fixture on
  first paint;
- `ProgressiveSymbolWorkstation` renders summary first and loads chart-core,
  technicals, financials, news, comparison, and sources on demand;
- interval, range, chart type, comparison, and active surface remain URL-backed;
- the client uses a same-origin runtime proxy;
- unrelated ProductNav RSC prefetch is disabled;
- Watchlist adds Price, Performance, Risk, Financials, and Technicals modes plus
  temporary sort/group controls;
- cache-derived watchlist metrics include 1W/1M/3M return, 1M realized
  volatility, average volume, RSI, SMA20/50, and trend state;
- FinanceChart now respects the actual container height.

## Compatibility

The existing full workstation and `chart` delivery remain intact. Streamlit is
still an internal lab; reusable behavior remains in `lib/`, `backend/api`, and
`apps/web`.

## Honest Gaps

- watchlist fundamentals are unavailable unless a bounded future materializer
  supplies them;
- earnings, dividends, alerts, import/export, and hosted sync are not present;
- offline mode shows a compact deterministic summary and an unavailable chart,
  not fake current data;
- no execution, advice, auth, billing, always-on scheduler, or paid dependency
  was added.

## Prepared Provider Path

A masked AAPL live smoke through existing adapters succeeded:

- Alpha Vantage + Finnhub breadth: `live/fresh`, 12 normalized metrics;
- exact company news: `live/fresh`, 3 bounded rows;
- earnings context: `live/fresh`, 12 bounded rows;
- each contract reported two source-register rows and no data gap.

The smoke also found and fixed a registry alias mismatch: the canonical
`ALPHAVANTAGE_API_KEY` now marks the Alpha Vantage layer/provider configured,
while `ALPHA_VANTAGE_API_KEY` remains a compatibility alias.
