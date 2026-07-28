from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.api_contracts import build_api_market_map_screener_payload
from lib.market_refresh_scheduler import run_market_refresh_schedule
from lib.market_snapshot_store import refresh_market_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one or more bounded Market Map refresh jobs.")
    parser.add_argument("--period", default="1y", choices=("3mo", "6mo", "1y"))
    parser.add_argument("--snapshot-dir", type=Path, default=None)
    parser.add_argument("--snapshot-retention", type=int, default=5)
    parser.add_argument("--history-retention", type=int, default=100)
    parser.add_argument("--interval-seconds", type=float, default=21_600)
    parser.add_argument("--loop", action="store_true", help="Continue until interrupted; default is one-shot.")
    parser.add_argument("--max-runs", type=int, default=None, help="Optional bounded run count in loop mode.")
    parser.add_argument("--fixture", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    stop = threading.Event()

    def execute() -> dict:
        health = refresh_market_snapshot(
            builder=lambda: build_api_market_map_screener_payload(
                include_runtime=not args.fixture,
                period=args.period,
            ),
            base_dir=args.snapshot_dir,
            retention=args.snapshot_retention,
            history_retention=args.history_retention,
        )
        print(json.dumps({"event": "market_snapshot_refresh_finished", **health}, sort_keys=True))
        return health

    max_runs = args.max_runs if args.loop else 1
    try:
        results = run_market_refresh_schedule(
            refresh=execute,
            interval_seconds=args.interval_seconds,
            max_runs=max_runs,
            stop_event=stop,
        )
    except KeyboardInterrupt:
        stop.set()
        print(json.dumps({"event": "market_snapshot_scheduler_stopped", "reason": "keyboard-interrupt"}))
        return 130
    return 0 if results and all(row.get("status") == "succeeded" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

