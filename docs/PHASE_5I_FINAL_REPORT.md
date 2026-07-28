# Phase 5I Final Report

Updated: 2026-06-20

## Verdict

Phase 5I is complete as a useful Market Map And Screener MVP, not as Finviz-level discovery parity. The durable Product Parity Master Goal remains active.

The previous defect was substantive: the web screener route exposed contract diagnostics and fixture cards while the existing Python screener runtime was invisible to users. The new product route now turns that runtime into an inspectable daily discovery workflow.

## Delivered

- Canonical `/?view=market-map` product route and navigation.
- 60-row live/cache yfinance equity universe when the free public provider succeeds.
- Separate market-data and local static taxonomy truth.
- Sector hierarchy, market-cap tile sizing, one-day return colors, breadth summary, search/filter/sort, selected-instrument context, and source link.
- Transparent rank formula, risk/return scatter, ranked table, and up-to-four-symbol comparison tray.
- URL persistence for runtime mode, asset class, sector, freshness, sort, direction, selection, and comparison.
- Ten-minute TTL, single-flight fetch, and labeled one-hour stale fallback.
- Deterministic 30-row fixture fallback with no secret leakage.
- Reproducible production-Chrome visual QA for desktop, mobile, and fallback.

## Metric Semantics

- Heatmap size: runtime market cap; deterministic relative weight in fixture mode.
- Heatmap color: one-day return.
- Scatter X: annualized realized volatility.
- Scatter Y: one-month return.
- Rank: 55% one-month return percentile, 30% inverse-volatility percentile, and 15% drawdown-resilience percentile.
- Missing required return or volatility makes a row rank-ineligible; it is never treated as zero.

These are descriptive research calculations, not recommendations.

## Runtime Evidence

The preflight and final API runtime both returned 60 usable equity rows from the existing yfinance batch-history path. The result was fresh on cold fetch and cached within the runtime TTL. Local sector/industry/exchange metadata remains explicitly static/proxy and is not claimed to be authoritative current S&P 500 membership.

## Visual Evidence

- `review_workspace/phase5i_visual/baseline-screener-diagnostics.png`
- `review_workspace/phase5i_visual/market-map-live-desktop.png`
- `review_workspace/phase5i_visual/market-map-live-mobile.png`
- `review_workspace/phase5i_visual/market-map-fixture-fallback.png`

Final assertions: desktop 60 rows/tiles/table rows and 50 scatter points; selected-sector mobile 5 rows/tiles with a 358x664 heatmap; fixture fallback 30 rows/tiles/scatter points; URL state persisted; browser console errors were zero.

## Clean-Room Boundary

FinanceDatabase MIT code was semantically reviewed for filter taxonomy, but no external dataset rows or code were copied. OpenBB AGPL models, Finviz, TradingView, Koyfin, and Bloomberg were behavior references only. The implementation is first-party Python, React, TypeScript, SVG, and CSS.

## Remaining Product Gaps

- The universe is 60 locally registered equities, not a complete authoritative index or global equity/ETF/crypto universe.
- yfinance is delayed public data and a cold fetch takes roughly one minute.
- The hierarchy is a stable flex layout, not a squarified treemap.
- Only AAPL currently links to a verified equity workstation.
- Fundamentals, estimate revisions, saved screens, alerts, and richer factor filters remain absent.
- Options, portfolio, and durable research-memory workflows remain below the benchmark target.

## Next Slice

Phase 5J is Options And Quant Workstation: verified chain acquisition, quality gates, Greeks, IV term/surface views, scenario research, and evidence-bound GEX only where data supports it.

The durable master goal must not be marked complete after this phase.
