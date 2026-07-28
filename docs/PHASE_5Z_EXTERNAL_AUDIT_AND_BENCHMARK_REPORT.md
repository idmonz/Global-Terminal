# Phase 5Z External Audit And Benchmark Report

Updated: 2026-07-01

## Audit Coverage

The required archive audit was rerun against `external (2)/external` before
implementation:

- 28 ZIP archives and 51,305 entries inventoried;
- 38,623 non-vendored text/code files indexed;
- 8,742,912 lines indexed;
- 556 vendored text files and 38 oversized text files skipped by the declared
  mechanical line-inventory policy;
- license classification: 18 direct-use-allowed, 6 behavior-only, 3 needs-review,
  and 1 blocked.

Artifacts:

- `review_workspace/external2_analysis/phase5z/external_zip_inventory.json`
- `review_workspace/external2_analysis/phase5z/external_line_inventory.json`
- `review_workspace/external2_analysis/phase5z/external_license_matrix.json`
- `review_workspace/external2_analysis/phase5z/external_feature_candidates.json`

This is traceable mechanical coverage, not a claim that millions of lines received
individual human semantic review.

## Scoped Reference Review

- Finviz and the supplied heatmap image informed dense hierarchy, metric legend,
  discovery filters, and selected-symbol continuity.
- TradingView informed independent size/color controls and detail drill-through.
- OpenBB informed source-aware widget boundaries and explicit provider state.
- OpenStock and OpenBB are AGPL behavior-only references.
- yfinance remains behind the existing Apache-2.0 provider boundary.
- FinanceDatabase, ai-website-cloner-template, and superloopy are MIT references,
  but no rows, source, visual assets, or trade dress were copied.
- OctoBot and the other required archives remain evidence candidates only unless an
  exact path and license review authorizes adaptation.

## Official Source Review

Nasdaq Trader symbol directories were selected for listing identity. They expose
symbol, name, exchange/listing venue, test-issue, ETF, financial status, and file
creation fields. They do not establish sector, industry, or index membership.

The SEC company ticker endpoint returned HTTP 403 in this environment and was not
promoted to live. Local sector/industry data remains `static/proxy`.

## Clean-Room Decision

Phase 5Z adopts benchmark behavior, not external implementation:

- first-party Python parsers and normalization;
- project-native React/CSS hierarchy and controls;
- no external source or image copied into the product;
- no implied S&P 500 or other index membership;
- no missing fundamental, taxonomy, or market value converted to zero.

## Remaining Benchmark Gap

The current 137-row online view is materially broader than the former 60-row map,
but it is not Finviz full-market coverage. Only 60 rows have reviewed local
taxonomy, index membership is not authoritative, and the Yahoo observation boundary
is delayed/public and not a licensed real-time feed.
