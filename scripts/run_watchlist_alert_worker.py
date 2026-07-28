from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path

from lib.identity_tenancy import local_test_context
from lib.watchlist_alert_manager import WatchlistAlertManagerStore, run_alert_worker_once


def _enabled() -> bool:
    return str(os.getenv("GLOBAL_TERMINAL_ALERT_WORKER_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded local stored-observation alert evaluator.")
    parser.add_argument("--alias", default="analyst-a", choices=("analyst-a", "analyst-b"))
    parser.add_argument("--db-path", default=os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or "")
    parser.add_argument("--loop", action="store_true", help="Repeat while explicitly enabled; default is one run.")
    parser.add_argument("--interval-seconds", type=int, default=int(os.getenv("GLOBAL_TERMINAL_ALERT_WORKER_INTERVAL_SECONDS") or 300))
    args = parser.parse_args()

    if not _enabled():
        print(json.dumps({"status": "disabled", "reason": "GLOBAL_TERMINAL_ALERT_WORKER_ENABLED is false", "provider_call_count": 0}))
        return 2
    if not args.db_path:
        print(json.dumps({"status": "blocked", "reason": "GLOBAL_TERMINAL_ACCOUNT_DB_PATH is required", "provider_call_count": 0}))
        return 2

    interval = max(60, min(int(args.interval_seconds), 86_400))
    context = local_test_context(args.alias)
    store = WatchlistAlertManagerStore(Path(args.db_path))
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)

    while True:
        result = run_alert_worker_once(context, store=store)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if not args.loop or stopping:
            break
        time.sleep(interval)
    store.mark_worker_state(context, "stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

