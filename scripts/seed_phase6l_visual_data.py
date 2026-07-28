from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.research_workspace_db import execute_query, json_dumps


NOW = datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc)


def _snapshot(symbol: str, price: float, *, status: str = "cached") -> dict:
    return {
        "symbol": symbol,
        "asset_class": "equity",
        "quote": {
            "last_price": price,
            "provider": "phase6l.visual-fixture",
            "source_url": f"https://example.invalid/{symbol.lower()}",
            "source_status": status,
            "retrieved_at": "2026-07-10T07:00:00+00:00",
            "observed_at": "2026-07-09T20:00:00+00:00",
        },
        "performance": {"return_1w_pct": 2.0, "return_1m_pct": 4.0, "return_3m_pct": 6.0},
        "financials": {"metrics": {"market_cap": 100_000_000_000, "pe_ratio": 25.0}},
        "catalysts": {"earnings": [], "dividends": [], "news": []},
        "source_status": status,
        "fetched_at": "2026-07-10T07:00:00+00:00",
        "source_register": [
            {
                "provider": "phase6l.visual-fixture",
                "source_url": f"https://example.invalid/{symbol.lower()}",
                "source_status": status,
                "fetched_at": "2026-07-10T07:00:00+00:00",
            }
        ],
    }


def _safe_review_path(raw_path: str) -> Path:
    root = Path(__file__).resolve().parents[1]
    review_root = (root / "review_workspace").resolve()
    target = Path(raw_path)
    if not target.is_absolute():
        target = root / target
    target = target.resolve()
    if review_root not in target.parents:
        raise SystemExit("Visual seed databases must stay under review_workspace.")
    return target


def seed(db_path: Path, *, reset: bool) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if reset and db_path.exists():
        db_path.unlink()
    execute_query(
        """
        INSERT OR REPLACE INTO watchlist_collections (
            list_id, name, position, active, created_at, updated_at, metadata_json
        ) VALUES ('primary', 'Phase 6L Daily Radar', 0, 1, ?, ?, '{}')
        """,
        (NOW.isoformat(), NOW.isoformat()),
        db_path=db_path,
    )
    for position, symbol in enumerate(("AAPL", "TSLA")):
        execute_query(
            """
            INSERT OR REPLACE INTO watchlist_items (
                item_id, watchlist_id, position, item_type, symbol, display_name,
                asset_class, exchange, tags, watch_reason, source, active,
                created_at, updated_at, metadata_json
            ) VALUES (?, 'primary', ?, 'equity', ?, ?, 'equity', 'NASDAQ',
                      '[]', ?, 'phase6l-visual-local', 1, ?, ?, '{}')
            """,
            (
                f"phase6l_item_{position}",
                position,
                symbol,
                f"{symbol} Visual QA",
                f"private local thesis for {symbol}",
                NOW.isoformat(),
                NOW.isoformat(),
            ),
            db_path=db_path,
        )
    snapshots = (
        [_snapshot("AAPL", 100.0), _snapshot("TSLA", 200.0)],
        [_snapshot("AAPL", 108.0), _snapshot("TSLA", 194.0, status="stale")],
    )
    for index, rows in enumerate(snapshots):
        started = NOW - timedelta(hours=2 - index)
        execute_query(
            """
            INSERT OR REPLACE INTO watchlist_materialization_jobs (
                job_id, list_id, status, requested_count, completed_count,
                provider_call_budget, provider_call_count, interval, range_name,
                started_at, completed_at, rows_json, created_at
            ) VALUES (?, 'primary', 'completed', 2, 2, 8, 0, '1d', '3mo', ?, ?, ?, ?)
            """,
            (
                f"phase6l_visual_job_{index}",
                started.isoformat(),
                started.isoformat(),
                json_dumps(rows),
                started.isoformat(),
            ),
            db_path=db_path,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed isolated Phase 6L visual QA research data.")
    parser.add_argument("--db-path", default="review_workspace/phase6l_visual/local-phase6l.db")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    target = _safe_review_path(args.db_path)
    seed(target, reset=args.reset)
    print(f"Seeded Phase 6L visual data: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
