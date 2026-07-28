# Phase 6L Performance Report

Updated: 2026-07-10

Command:

```powershell
python scripts/benchmark_phase6l.py --page-url "http://127.0.0.1:3064/?view=watchlist-desk&mode=fixture&list=primary&selected=AAPL"
```

| Check | Observed | Budget | Result |
|---|---:|---:|---|
| Account summary p95 | 23.823 ms | 100 ms | pass |
| Sync status p95 | 7.810 ms | 100 ms | pass |
| 25-record reconciliation p95 | 7.875 ms | 75 ms | pass |
| Sync request | 6,957 bytes / 25 records | 30KB / 25 | pass |
| Initial Watchlist HTML | 76,587 bytes | 100KB | pass |
| Hidden account requests before open | 0 | 0 | pass |
| Market-provider calls during sync/reconcile | 0 | 0 | pass |

Evidence: `review_workspace/phase6l_performance/summary.json`.

Hosted p95 is intentionally unreported because no hosted adapter was contacted.
That external prerequisite, not local CPU/SQLite work, is the current sync
performance bottleneck.

