# Phase 6G Performance Report

Updated: 2026-07-03

## Final Measurements

| Gate | Result | Budget |
|---|---:|---:|
| Five-symbol diff p50 | 0.50 ms | - |
| Five-symbol diff p95 | 0.95 ms | < 100 ms |
| Five-symbol diff maximum, 1,000 runs | 3.76 ms | - |
| Representative diff payload | 3,702 bytes | < 100 KB |
| Change Inbox initial HTML | 78,558 bytes | < 100 KB |
| Change scan/filter provider requests | 0 | 0 |
| Phase 6E AAPL desktop useful chart | 713 ms | no regression |
| Phase 6E TSLA mobile useful chart | 615 ms | no regression |
| Chart-core payload | about 69.8 KB | no regression |
| Background RSC prefetches | 0 | 0 |

## Optimization

The first integrated fixture serialized the same Research Snapshot rows under
both `latest_job` and `latest_success`, increasing initial HTML to 127,382
bytes. Job metadata now omits the duplicate `rows` arrays because normalized
Watchlist items and the dedicated change contract already carry the required
public evidence. Final HTML is 78,558 bytes.

No provider, exact panel, AI, or broad-universe call occurs during saved diff,
filter, sort, or selection.

