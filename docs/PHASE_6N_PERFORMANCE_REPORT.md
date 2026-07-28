# Phase 6N Performance Report

Updated: 2026-07-13

Evidence: `review_workspace/phase6n_performance/summary.json`.

## Local Benchmarks

| Check | Result | Budget | Verdict |
|---|---:|---:|---|
| 25-symbol-equivalent planning p95 | 1.706 ms | 50 ms | pass |
| five-symbol atomic persist/diff p95 | 23.781 ms | 75 ms | pass |
| Attention compose p95 | 0.454 ms | 75 ms | pass |
| Attention filter/rank p95 | 0.033 ms | 50 ms | pass |
| run-summary payload | 3,528 bytes | 35,000 bytes | pass |
| provider calls during triage | 0 | 0 | pass |
| initial Attention HTML | 89,554 bytes | 100,000 bytes | pass |

The planner metric executes five independent five-symbol plans because five is
the product hard cap; it does not silently expand the user-visible run limit.

## Initial Payload Repair

The runtime Attention envelope contained 19 `all_items`, producing 134KB HTML.
The first repair reached 100,008 bytes, which was only below a binary 100KiB
interpretation. The final boundary sends ten initial rows, retains the actual
`total_row_count`, and measures 89,554 bytes through the production Next server.
Full account detail remains available through the explicit account API.

## Network Separation

Provider and hosted Supabase latency are excluded from local planning,
persistence, and triage measurements. The controlled source-backed AAPL run
took about eight seconds end to end. That network result is reported as live
evidence, not folded into a misleading local p95.
