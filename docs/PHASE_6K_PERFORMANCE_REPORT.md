# Phase 6K Performance Report

Updated: 2026-07-10

Harness: `python scripts/benchmark_phase6k.py --page-url <local product URL>`

| Gate | Result | Budget | Verdict |
|---|---:|---:|---|
| 25-row import preview p95 | 21.703 ms | 50 ms | pass |
| Import preview JSON | 11,444 bytes | 20,000 bytes | pass |
| Tenant desk summary p95 | 39.409 ms | 75 ms | pass |
| Tenant desk JSON | 21,355 bytes | 30,000 bytes | pass |
| Acknowledge p95, 25 samples | 15.246 ms | 50 ms | pass |
| Initial Watchlist HTML | 76,525 bytes | 100,000 bytes | pass |
| Saved inbox scan provider calls | 0 | 0 | pass |

Phase 6I's prior 28.8 KB / 77.15 ms p95 operations gate remains below its 30
KB / 100 ms budget and the Phase 6H/6I regression workspace rendered in the
final browser harness.

These are deterministic local SQLite/contract measurements. They do not
measure hosted Postgres, network delivery, multi-region latency, or production
concurrency.
