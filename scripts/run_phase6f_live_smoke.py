from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.env_loader import get_env_var
from lib.watchlist_desk import (
    add_watchlist_symbol,
    build_watchlist_desk_contract,
    create_watchlist,
    materialize_watchlist,
)


SYMBOLS = ("AAPL", "TSLA", "JNJ", "TTE", "TMUS")


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    db_path = output_dir / f"phase6f-live-{stamp}.db"
    create_watchlist("Phase 6F Live QA", list_id="phase6f-live", db_path=db_path)
    for symbol in SYMBOLS:
        add_watchlist_symbol(
            "phase6f-live",
            symbol,
            asset_class="equity",
            db_path=db_path,
        )
    job = materialize_watchlist(
        "phase6f-live",
        interval="1d",
        range_name="3mo",
        max_symbols=5,
        db_path=db_path,
    )
    contract = build_watchlist_desk_contract(
        list_id="phase6f-live",
        selected_symbol="AAPL",
        db_path=db_path,
    )
    rows = []
    for row in contract.get("items", []):
        financials = row.get("advanced") or {}
        catalysts = row.get("catalysts") or {}
        rows.append(
            {
                "symbol": row.get("symbol"),
                "status": row.get("refresh_status"),
                "source_status": row.get("source_status"),
                "last_price": row.get("last_price"),
                "change_pct": row.get("change_pct"),
                "performance_1m_pct": financials.get("return_1m_pct"),
                "market_cap": financials.get("market_cap"),
                "pe_ratio": financials.get("pe_ratio"),
                "eps": financials.get("eps"),
                "earnings_count": len(catalysts.get("earnings") or []),
                "dividend_count": len(catalysts.get("dividends") or []),
                "exact_news_count": len(catalysts.get("news") or []),
                "next_event": (catalysts.get("next_event") or {}).get("event_date")
                or (catalysts.get("next_event") or {}).get("ex_dividend_date"),
                "fetched_at": row.get("refresh_fetched_at"),
                "data_gap": row.get("refresh_data_gap"),
            }
        )
    report = {
        "phase": "6F",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": db_path.name,
        "configured_keys": {
            "ALPHAVANTAGE_API_KEY": bool(get_env_var("ALPHAVANTAGE_API_KEY")),
            "FINNHUB_API_KEY": bool(get_env_var("FINNHUB_API_KEY")),
        },
        "job": {
            key: job.get(key)
            for key in (
                "status",
                "requested_count",
                "completed_count",
                "failed_count",
                "skipped_count",
                "provider_call_budget",
                "provider_call_count",
                "queue_depth",
                "duration_ms",
                "started_at",
                "completed_at",
                "last_error",
            )
        },
        "provider_budget": job.get("provider_budget"),
        "summary": contract.get("summary"),
        "rows": rows,
        "private_values_included": False,
        "not_financial_advice": True,
    }
    output_path = output_dir / f"phase6f-live-{stamp}.json"
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    return {**report, "report_file": str(output_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one bounded Phase 6F live provider smoke.")
    parser.add_argument(
        "--output-dir",
        default="review_workspace/phase6f_live",
        help="Directory for the isolated SQLite database and sanitized JSON report.",
    )
    args = parser.parse_args()
    print(json.dumps(run(Path(args.output_dir)), indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
