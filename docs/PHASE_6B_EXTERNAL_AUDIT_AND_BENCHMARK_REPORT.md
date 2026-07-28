# Phase 6B External Audit And Benchmark Report

Updated: 2026-07-01

## Mechanical Audit

The full deterministic archive audit was rerun into
`review_workspace/external2_analysis/phase6b`.

- archives: 28;
- entries: 51,305;
- indexed non-vendored text/code files: 38,623;
- indexed lines: 8,742,912;
- skipped vendored files: 556;
- skipped oversized files: 38;
- archive hash changes from Phase 6A: zero;
- license classes: 18 direct-use, 6 behavior-only, 3 needs-review, 1 blocked.

This proves mechanical coverage, not individual human semantic review of every
line.

## Scoped Clean-Room Evidence

- OpenBB and OpenStock remained AGPL behavior-only references.
- FinanceDatabase informed schema/taxonomy behavior; no external rows were copied.
- Supabase informed bounded operational-history concepts; no hosted dependency
  was added.
- yfinance remained behind the existing Apache-2.0 provider boundary.
- official Nasdaq Trader directories supplied current listing identity.
- the SEC ticker/exchange directory supplied CIK/ticker/exchange identity.
- supplied Finviz/TradingView screenshots informed density and interaction only.

No external source, row dataset, screenshot, font, brand, or trade dress was copied
into the product.

## Official Live Verification

- Nasdaq Trader's current directory visibly includes common shares, ETFs, rights,
  units, warrants, preferreds, and other instruments. The project therefore
  performs an explicit supported-security filter rather than treating every row as
  common equity.
- SEC's current ticker/exchange JSON provides CIK, company name, ticker, and
  exchange identity; it does not provide sector, GICS, or index membership.
- SEC EDGAR documentation confirms that public filing/XBRL APIs are keyless but
  subject to fair-access identification and limits.
- AAPL market evidence was independently checked against a current market lookup:
  289.36 USD and roughly +2.6% during the observed session, consistent with the
  product's delayed 289.36 / +2.70% row.

## Benchmark Position

Global Terminal now provides 333 useful, official-listing-matched heatmap rows,
11 canonical sectors, hierarchy, independent size/color encodings, exact detail,
and source truth. It remains below Finviz/TradingView breadth because:

- 333 rows are not a full US market;
- only 60 rows have reviewed industry labels;
- 273 rows use provider sector-query classification;
- no official GICS or authoritative index membership is claimed;
- only a bounded subset has full technical/rank history and workstation support.

