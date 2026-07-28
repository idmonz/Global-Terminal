# Phase 6E Next Goal Rationale

Updated: 2026-07-03

## Evidence

Phase 6E removes the measured direct-workstation delivery bottleneck and makes
one exact-symbol journey fast and progressive. The next daily-use gap is no
longer initial rendering.

The Watchlist advanced shell exists, but fixture/cache rows often lack
fundamentals, earnings, dividends, and exact news. Fetching these per row would
reintroduce fan-out and rate-limit risk. Alerts and hosted accounts would also
be premature without a durable materialization ledger.

The existing AAPL Alpha Vantage/Finnhub smoke already returned 12 normalized
metrics, 3 bounded exact-news rows, and 12 earnings rows as `live/fresh`.
Therefore Phase 6F should compose and budget proven adapters, not add another
provider layer.

## Selected Phase 6F

**Bounded Research Snapshot And Catalyst Monitor.**

Build one bounded list-level materialization that reuses Alpha Vantage,
Finnhub, SEC, yfinance, and existing news/cache adapters to produce current
price/performance, fundamentals, earnings/dividend events, and exact catalysts
with provider budgets, LKG, provenance, and no per-render fan-out. Make the
Watchlist -> exact asset -> catalyst/source -> return journey production-grade.

Auth, billing, broker execution, broad alerts, and arbitrary dashboard layout
remain deferred.
