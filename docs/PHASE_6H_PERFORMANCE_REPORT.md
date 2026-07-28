# Phase 6H Performance Report

Updated: 2026-07-03

## Final Measurements

Fixture measurements used 25 HTTP iterations and zero provider calls.

| Gate | Result | Budget |
|---|---:|---:|
| Workspace manifest payload | 11,760 bytes | < 30 KB |
| Workspace manifest p50/p95 | 7.69 / 10.16 ms | - |
| Initial analyst HTML | 83,508 bytes | < 100 KB |
| Chart-core payload | 47,282 bytes | no material Phase 6E regression |
| Chart-core p50/p95 | 58.35 / 66.11 ms | - |
| Financial p95 | 8.23 ms | < 250 ms |
| Catalyst p95 | 6.79 ms | < 250 ms |
| Source p95 | 7.41 ms | < 250 ms |
| Desktop initial panel requests | 3 secondary | <= 4 total |
| Hidden mobile requests before action | 0 | 0 |
| Mobile request after Financials selection | 1 | 1 |
| Background RSC prefetches | 0 | 0 |
| Slow-panel chart layout shift | 0 px | 0 px |
| ETag conditional responses | 304 for all measured routes | required |

## Optimization

The first saved-primary implementation serialized the same chart under
`chart_views.price` and `chart_specs`, leaving initial HTML at 99,796 bytes.
The browser uses `chart_views.price`; removing the duplicate plus unused
capability rows reduced final HTML to 83,508 bytes while retaining all 48
fixture candles.

Non-timeframe panel cache identities use exact symbol plus panel identity.
Changing TSLA from `1d` to `1h` therefore requested only the exact TSLA
`chart-core` panel, not financial, catalyst, or source panels.

Reproducible output:

`review_workspace/phase6h_performance/summary.json`

