# Phase 6A External Audit And Benchmark Report

Updated: 2026-07-01

## Mechanical Coverage

The full archive audit was rerun into
`review_workspace/external2_analysis/phase6a`.

- archives: 28;
- archive entries: 51,305;
- indexed non-vendored files: 38,623;
- indexed text/code lines: 8,742,912;
- archive hash changes since Phase 5Z: zero;
- license classification: 18 direct-use, 6 behavior-only, 3 needs-review,
  1 blocked.

This proves mechanical coverage, not line-by-line human semantic review.

## Scoped Clean-Room Review

- OpenBB and OpenStock informed source-aware widget and provider behavior only.
- FinanceDatabase informed taxonomy/schema behavior; no data rows were copied.
- Supabase informed atomic persistence and health concepts only; no hosted
  dependency was added.
- yfinance remains behind the existing Apache-2.0 provider boundary.
- supplied screenshots and benchmark products informed density, hierarchy, and
  interaction behavior only.
- no external code, rows, screenshot assets, fonts, branding, or trade dress were
  copied.

## Current Benchmark Comparison

TradingView documents independent heatmap size/color settings, sector grouping,
group drilldown, tooltip/detail navigation, and symbol-page click-through. Global
Terminal now has those core interaction behaviors, plus explicit source and
snapshot truth. It still lacks TradingView's broad asset coverage, display
customization, sharing, and production streaming.

The SEC documents `companyfacts` as a no-key JSON API updated as filings are
disseminated. Global Terminal now preserves reviewed concepts, units, periods,
forms, filed dates, accessions, and source state. It does not yet expose filing
documents, footnotes, company extensions, or broad cross-company comparison.

Alpha Vantage documents a symbol-filterable earnings calendar. The current
workstation separates scheduled and reported rows and keeps unavailable values
null. Provider terms and free-tier limits remain binding.

## Residual Gaps

- 137 observed/listed rows are useful but far below broad Finviz coverage.
- taxonomy is available for 60 of 137 rows and is local static/proxy.
- refresh is an explicit CLI, not a proven always-on scheduler.
- the product lacks production telemetry, hosted tenancy, entitlements, and CDN.
- SEC facts need cross-company reconciliation and filing drilldown.

