# Phase 6F Performance Report

Updated: 2026-07-03

## Final Measurements

All measurements used the local production Next server on port 3052 and the
FastAPI runtime on port 8008.

| Surface | Result | Budget |
|---|---:|---:|
| AAPL summary API p50 / p95, 20 warm reads | 28.64 / 35.15 ms | < 500 ms |
| AAPL summary body | 19,832 bytes | < 100 KB |
| AAPL chart-core body | 69,779 bytes | < 100 KB |
| AAPL desktop useful chart | 660 ms | < 1.5 s |
| TSLA mobile useful chart | 536 ms | < 1.5 s |
| Background ProductNav RSC prefetches | 0 | 0 |
| Watchlist mode-change exact-panel requests | 0 | 0 |

The single 217 ms summary outlier remained below the 500 ms budget; p95 was
35.15 ms.

## Provider Budget

The five-symbol snapshot cannot exceed 16 planned calls. A warm smoke used one
history request and 15 cache hits. Sort, group, view-mode, and saved-row
selection do not fan out to providers.

## Regression

Phase 6E progressive-delivery budgets remain intact after Phase 6F. The
Catalyst panel is additive and does not restore the former 1.07 MB direct
workstation document.
