# Phase 6B Scheduler And Refresh History

Updated: 2026-07-01

## Components

- `lib/market_refresh_scheduler.py`: bounded one-shot/loop runner with stop event;
- `scripts/run_market_refresh_scheduler.py`: local CLI;
- `market_refresh_history.v1`: bounded operational ledger;
- `GET /api/market-refresh-history?limit=20`;
- `GET /api/market-refresh-health`.

## Commands

One shot:

```powershell
python scripts/run_market_refresh_scheduler.py --period 1y
```

Bounded local loop:

```powershell
python scripts/run_market_refresh_scheduler.py --loop --max-runs 4 --interval-seconds 21600
```

The loop exits cleanly on Ctrl+C. A file lock plus process lock prevents overlap.
Busy attempts are recorded without deleting another process's lock.

## Windows Task Scheduler

The recommended production-like local setup is one-shot execution from Task
Scheduler every six hours:

```text
Program: <python executable>
Arguments: scripts/run_market_refresh_scheduler.py --period 1y
Start in: <repo root>
Policy: do not start a new instance when the previous task is running
```

This repository documents the setup but does not claim that a Windows task was
installed or is always running.

## History Fields

The bounded history records job/status, start/end, duration, last success, generic
error, rows, bytes, provider calls/sources, classification/industry/unclassified
counts, exclusions, snapshot version, and content hash. Secrets, paths, holdings,
notes, and raw exception messages are rejected or omitted.

Final observed one-shot:

- status: succeeded;
- duration: 14.9 seconds;
- rows: 333;
- payload: 865,342 bytes;
- provider calls: 15 observed after cache reuse;
- classification: 333;
- industry: 60;
- excluded observations: 417.

