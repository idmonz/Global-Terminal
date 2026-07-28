from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.api_contracts import build_api_market_map_screener_payload
from lib.market_snapshot_store import refresh_market_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh the local materialized Market Map snapshot.")
    parser.add_argument("--period", default="1y", choices=("3mo", "6mo", "1y"), help="History window used for rank factors.")
    parser.add_argument("--snapshot-dir", type=Path, default=None, help="Optional local snapshot directory override.")
    parser.add_argument("--retention", type=int, default=5, help="Number of immutable snapshots to retain (1-50).")
    parser.add_argument("--fixture", action="store_true", help="Materialize deterministic fixture data without provider calls.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    health = refresh_market_snapshot(
        builder=lambda: build_api_market_map_screener_payload(
            include_runtime=not args.fixture,
            period=args.period,
        ),
        base_dir=args.snapshot_dir,
        retention=args.retention,
    )
    print(json.dumps({"event": "market_snapshot_refresh_finished", **health}, ensure_ascii=True, sort_keys=True))
    return 0 if health.get("status") == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
