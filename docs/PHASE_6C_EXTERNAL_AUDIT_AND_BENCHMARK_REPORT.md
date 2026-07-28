# Phase 6C External Audit And Benchmark Report

Updated: 2026-07-02

## Mechanical Audit

The deterministic external audit was rerun into
`review_workspace/external2_analysis/phase6c`.

- archives: 28;
- file entries: 51,305;
- indexed non-vendored text/code files: 38,623;
- indexed lines: 8,742,912;
- vendored files skipped: 556;
- oversized files skipped: 38;
- read errors: zero;
- archive hash changes from Phase 6B: zero;
- license classes: 18 direct-use, 6 behavior-only, 3 needs-review, 1 blocked.

This is complete mechanical inventory coverage, not a claim that a person
semantically reviewed every line. The generated inventory, line index, license
matrix, and feature candidates remain review evidence only.

## Clean-Room Boundary

- OpenBB, OpenStock, WorldMonitor, and other AGPL references remained
  behavior-only.
- worldview and unclear or missing-license projects remained behavior-only.
- FinanceDatabase informed taxonomy/schema concepts; no external row dataset was
  copied.
- yfinance remained behind the existing Apache-2.0 provider boundary.
- supplied Finviz, TradingView, OpenBB, terminal, heatmap, newsroom, and War Room
  screenshots informed density and interaction comparison only.
- no external source file, screenshot, font, brand asset, dataset, or trade dress
  was copied into the product.

## Current Official Benchmark Check

Official product documentation was checked again on 2026-07-02:

- Finviz describes a screener spanning Nasdaq, NYSE, and AMEX with combined
  fundamental/technical filters, rich output, fast navigation, and instant
  updates: <https://finviz.com/help/screener>.
- TradingView documents symbol search leading directly to a chart or overview,
  with symbol-specific fundamentals, news, technicals, comparison, watchlists,
  alerts, and calendars:
  <https://www.tradingview.com/support/solutions/43000746464-getting-started-with-supercharts/>
  and
  <https://www.tradingview.com/support/solutions/43000745825-mastering-the-tradingview-watchlists/>.
- OpenBB Workspace documents source-aware widgets, synchronized parameters, and
  configurable dashboards:
  <https://docs.openbb.co/workspace> and
  <https://docs.openbb.co/workspace/analysts/widgets/overview>.
- SEC documents that submissions and XBRL company-facts APIs are keyless and
  update throughout the day as filings are disseminated:
  <https://www.sec.gov/search-filings/edgar-application-programming-interfaces>.

## Measured Product Position

| Capability | Phase 6B baseline | Phase 6C result | Remaining benchmark gap |
|---|---:|---:|---|
| Market Map identities | 333 | 333 | Not a full US equity universe |
| Exact workstation activation | 60 / 333 | 333 / 333 | Broader instruments/exchanges remain bounded |
| Runtime symbol directory | 90 static | 363 combined | No authoritative global security master |
| Exact non-AAPL visual proof | 0 in this slice | TSLA, JNJ, TTE, TMUS | No arbitrary global symbol proof |
| Chart/history | old static set | 62 rows and 180 rendered points for proof symbols | No drawings, custom studies, or streaming |
| Filing depth | mainly AAPL | exact CIK path; TSLA showed 44 SEC facts | Foreign/non-filer coverage varies honestly |
| Warm exact API | not broad | TSLA p50 181 ms, p95 250 ms | Cold provider fetch observed 12.8-14.8 s |
| First useful web paint | dead-end for 273 rows | 1.64-2.00 s in final warm proof | SSR response remains about 1.07 MB |

Phase 6C closes the most damaging discovery dead-end. It does not establish
Finviz full-universe breadth, TradingView chart-tool parity, OpenBB configurable
workspace composition, Bloomberg data licensing, or production streaming.

