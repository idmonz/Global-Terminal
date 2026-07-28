# Phase 6M Performance Report

Updated: 2026-07-13

Measured with `python scripts/benchmark_phase6m.py --samples 100` against the
production page and final visual summary.

| Check | Result | Budget | Verdict |
|---|---:|---:|---|
| Compose 100 stored rows p95 | 41.776ms | 75ms | pass |
| Filter/rank 100 rows p95 | 12.874ms | 50ms | pass |
| Review mutation p95 | 15.868ms | 50ms | pass |
| Initial API payload | 48,975B | 50,000B | pass |
| Initial Attention HTML | 80,155B | 100,000B | pass |
| Hidden account requests | 0 | 0 | pass |
| Triage-time provider calls | 0 | 0 | pass |

The review mutation includes the state change and bounded audit row in one
`BEGIN IMMEDIATE` transaction. The page serializes only the compact initial
Attention envelope; detail remains demand-loaded.

These are local stored-evidence and SQLite measurements. They do not represent
market-provider, hosted database, internet, or multi-region latency. Hosted
Supabase latency remains unmeasured while the schema and admin deployment gate
are unavailable.
