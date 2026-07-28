# Phase 6F External Audit And Benchmark Report

Updated: 2026-07-03

## Scope

The Phase 6F preflight re-ran the deterministic audit over all 28 required
archives in `external (2)/external`. Evidence is stored under
`review_workspace/external2_analysis/phase6f`.

| Evidence | Result |
|---|---:|
| Archives | 28 |
| Zip entries | 51,305 |
| Indexed non-vendored text/code files | 38,623 |
| Indexed lines | 8,742,912 |
| Feature candidates | 24 |
| Direct-use-allowed | 18 |
| Behavior-only | 6 |
| Needs review | 3 |
| Blocked | 1 |

The manifest indexes every archive entry. Semantic review is targeted by
feature and exact path; mechanical line indexing is not represented as human
understanding of every line.

## Clean-Room Decision

Phase 6F copied no external source, dataset, visual asset, font, or trade dress.
It used these behavior patterns:

- TradingView: advanced watchlist modes and compact event fields;
- OpenBB: source-aware widgets and explicit provider selection/status;
- Finviz: dense scan-first list hierarchy;
- Bloomberg-like terminals: compact identity, clock, event, and source context;
- OctoBot/OpenStock/yfinance/Zipline/Superloopy: process and domain evidence only,
  subject to the archive license matrix.

AGPL, mixed-license, missing-license, and unclear paths remain behavior-only or
blocked. Permissive status does not authorize copying without exact-path review
and retained notices.

## Official Benchmark Findings

- TradingView advanced watchlists combine configurable columns with earnings,
  dividends, and news context. Phase 6F adopts saved-row modes and event
  visibility, not TradingView visuals or code.
- OpenBB Workspace treats data source and widget state as visible product
  concepts. Phase 6F keeps a source register and freshness/caveat fields beside
  the research result.
- Alpha Vantage documents a standard free allowance of 25 requests/day.
  Phase 6F therefore caps a five-symbol refresh at five overview calls.
- Finnhub documents API-key authentication and HTTP 429 behavior. Phase 6F
  bounds earnings/news calls, reads cache first, and preserves saved rows when
  the provider is rate-limited.
- SEC fair-access guidance remains a maximum boundary; SEC facts are not added
  to the list-level fan-out plan.

## Sources

- https://www.tradingview.com/support/solutions/43000771546-watchlist-advanced-view-mode/
- https://docs.openbb.co/workspace/analysts/widgets/overview
- https://www.alphavantage.co/premium/
- https://finnhub.io/docs/api/quote
- https://www.sec.gov/filergroup/announcements-old/new-rate-control-limits

The current product is materially closer to a useful daily watchlist, but it is
not benchmark-grade and does not claim benchmark parity.
