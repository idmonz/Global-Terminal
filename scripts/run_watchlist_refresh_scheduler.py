from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.market_refresh_scheduler import run_market_refresh_schedule
from lib.watchlist_desk import materialize_watchlist


def _enabled(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, "")).strip() or default)
    except ValueError:
        return default


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded local watchlist Research Snapshot refresh.",
    )
    parser.add_argument("--list-id", default="primary")
    parser.add_argument("--interval", default="1d", choices=("1d",))
    parser.add_argument("--range", dest="range_name", default="3mo", choices=("3mo",))
    parser.add_argument("--max-symbols", type=int, default=5)
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=_float_env("WATCHLIST_REFRESH_INTERVAL_SECONDS", 21_600),
    )
    parser.add_argument("--loop", action="store_true", help="Run repeatedly only when explicitly enabled.")
    parser.add_argument("--max-runs", type=int, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if _enabled("WATCHLIST_REFRESH_KILL_SWITCH"):
        print(json.dumps({"event": "watchlist_scheduler_refused", "reason": "kill-switch"}, sort_keys=True))
        return 2
    if args.loop and not _enabled("WATCHLIST_BACKGROUND_REFRESH_ENABLED"):
        print(
            json.dumps(
                {
                    "event": "watchlist_scheduler_refused",
                    "reason": "background-disabled-by-default",
                    "recommended_action": "Set WATCHLIST_BACKGROUND_REFRESH_ENABLED=true only for an intentional local run.",
                },
                sort_keys=True,
            )
        )
        return 2

    stop = threading.Event()

    def execute() -> dict:
        result = materialize_watchlist(
            args.list_id,
            interval=args.interval,
            range_name=args.range_name,
            max_symbols=max(1, min(args.max_symbols, 5)),
        )
        event = {
            "event": "watchlist_snapshot_refresh_finished",
            "list_id": result.get("list_id"),
            "job_id": result.get("job_id"),
            "status": result.get("status"),
            "requested_count": result.get("requested_count"),
            "completed_count": result.get("completed_count"),
            "failed_count": result.get("failed_count"),
            "provider_call_count": result.get("provider_call_count"),
            "provider_call_budget": result.get("provider_call_budget"),
            "duration_ms": result.get("duration_ms"),
        }
        print(json.dumps(event, sort_keys=True))
        return result

    max_runs = args.max_runs if args.loop else 1
    try:
        results = run_market_refresh_schedule(
            refresh=execute,
            interval_seconds=max(60.0, args.interval_seconds),
            max_runs=max_runs,
            stop_event=stop,
        )
    except KeyboardInterrupt:
        stop.set()
        print(json.dumps({"event": "watchlist_scheduler_stopped", "reason": "keyboard-interrupt"}, sort_keys=True))
        return 130
    accepted = {"completed", "partial", "empty"}
    return 0 if results and all(str(row.get("status")) in accepted for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
