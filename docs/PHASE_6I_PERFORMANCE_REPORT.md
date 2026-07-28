# Phase 6I Performance Report

Updated: 2026-07-04

Machine-local production QA:

- FastAPI: `127.0.0.1:8061`
- Next.js production: `127.0.0.1:3061`
- iterations: 25, except initial HTML measured once

| Surface | Final | Budget | Result |
|---|---:|---:|---|
| Operations payload | 26,903 bytes | < 30,000 | pass |
| Operations p50 | 61.03 ms | evidence | pass |
| Operations p95 | 83.88 ms | < 100 ms | pass |
| Cached chart-core p50 | 9.47 ms | evidence | pass |
| Cached chart-core p95 | 22.90 ms | < 250 ms | pass |
| Cached chart-core maximum | 460.31 ms | cold sample | observed |
| Initial analyst HTML | 98,078 bytes | < 100,000 | pass |
| Provider calls during read benchmark | 0 | 0 | pass |

The cold chart sample still pays contract composition and serialization cost.
Short duplicate cache reads no longer repeat SQLite observation writes.

Phase 6E regression remained within its own useful-chart budget after a single
exact TSLA warm-up:

- AAPL useful chart: 991 ms, 62 rows, 69,779-byte chart panel;
- TSLA mobile useful chart: 915 ms, 62 rows, 69,812-byte chart panel;
- background prefetches: zero.

Raw evidence:

- `review_workspace/phase6i_performance/summary.json`
- `review_workspace/phase6e_visual_online/summary.json`

The response cache is bounded to 64 entries and five seconds. It is not a CDN,
distributed cache, or hosted invalidation service.
