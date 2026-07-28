from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.identity_tenancy import local_test_context
from lib.research_workspace_db import execute_query, json_dumps
from lib.tenant_research_desk import TenantResearchDeskStore


NOW = datetime(2026, 7, 10, 3, 0, tzinfo=timezone.utc)


def _snapshot(symbol: str, price: float) -> dict:
    return {
        "symbol": symbol,
        "asset_class": "equity",
        "quote": {
            "last_price": price,
            "provider": "phase6k.performance-fixture",
            "source_url": f"https://example.invalid/{symbol.lower()}",
            "source_status": "cached",
            "retrieved_at": "2026-07-10T02:00:00+00:00",
            "observed_at": "2026-07-09T20:00:00+00:00",
        },
        "performance": {}, "financials": {"metrics": {}},
        "catalysts": {"earnings": [], "dividends": [], "news": []},
        "source_status": "cached", "fetched_at": "2026-07-10T02:00:00+00:00",
    }


def _seed(db_path: Path) -> None:
    execute_query(
        "INSERT INTO watchlist_collections (list_id, name, position, active, created_at, updated_at, metadata_json) VALUES ('primary', 'Performance Radar', 0, 1, ?, ?, '{}')",
        (NOW.isoformat(), NOW.isoformat()), db_path=db_path,
    )
    symbols = [f"S{index:02d}" for index in range(25)]
    for position, symbol in enumerate(symbols):
        execute_query(
            """
            INSERT INTO watchlist_items (
                item_id, watchlist_id, position, item_type, symbol, display_name, asset_class,
                exchange, tags, watch_reason, source, active, created_at, updated_at, metadata_json
            ) VALUES (?, 'primary', ?, 'equity', ?, ?, 'equity', 'TEST', '[]', 'private benchmark note', 'phase6k-benchmark', 1, ?, ?, '{}')
            """,
            (f"benchmark_{position}", position, symbol, symbol, NOW.isoformat(), NOW.isoformat()), db_path=db_path,
        )
    for index, multiplier in enumerate((1.0, 1.08)):
        rows = [_snapshot(symbol, (100 + position) * multiplier) for position, symbol in enumerate(symbols)]
        timestamp = NOW - timedelta(hours=2 - index)
        execute_query(
            """
            INSERT INTO watchlist_materialization_jobs (
                job_id, list_id, status, requested_count, completed_count, provider_call_budget,
                provider_call_count, interval, range_name, started_at, completed_at, rows_json, created_at
            ) VALUES (?, 'primary', 'completed', 25, 25, 0, 0, '1d', '3mo', ?, ?, ?, ?)
            """,
            (f"benchmark_job_{index}", timestamp.isoformat(), timestamp.isoformat(), json_dumps(rows), timestamp.isoformat()),
            db_path=db_path,
        )


def _sample(callback, count: int) -> tuple[list[float], object]:
    durations = []
    result = None
    for _ in range(count):
        started = time.perf_counter()
        result = callback()
        durations.append((time.perf_counter() - started) * 1000)
    return durations, result


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def _metric(values: list[float], budget: float) -> dict:
    p95 = round(_p95(values), 3)
    return {"samples": len(values), "p50_ms": round(sorted(values)[len(values) // 2], 3), "p95_ms": p95, "budget_ms": budget, "passed": p95 <= budget}


def run(*, page_url: str | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="global-terminal-phase6k-") as temporary:
        root = Path(temporary)
        local_db = root / "local.db"
        account_db = root / "account.db"
        _seed(local_db)
        store = TenantResearchDeskStore(account_db_path=account_db, local_db_path=local_db)
        context = local_test_context("analyst-a")
        store.summary(context)
        preview_times, preview = _sample(lambda: store.preview_import(context, source_list_id="primary", limit=25), 50)
        imported = store.confirm_import(
            context,
            {
                "preview_id": preview["preview_id"],
                "candidate_ids": [row["candidate_id"] for row in preview["candidates"]],
                "consent": True,
                "idempotency_key": "phase6k-performance-import",
                "expected_version": 0,
                "destination_name": "Performance Radar",
            },
        )
        watchlist_id = imported["watchlist"]["resource_id"]
        summary_times, desk = _sample(lambda: store.build_contract(context), 50)
        rule = store.configure_rule(context, watchlist_id, enabled=True, cooldown_minutes=0, expected_version=0, now=NOW)
        scan = store.scan_inbox(context, watchlist_id, now=NOW)
        inbox = store.list_inbox(context, now=NOW)
        acknowledge_times = []
        for item in inbox[:25]:
            started = time.perf_counter()
            store.update_inbox_state(context, item["resource_id"], state="acknowledged", expected_version=item["version"], now=NOW)
            acknowledge_times.append((time.perf_counter() - started) * 1000)
        html_bytes = None
        if page_url:
            with urlopen(page_url, timeout=10) as response:  # noqa: S310 - caller controls local QA URL
                html_bytes = len(response.read())
        preview_bytes = len(json.dumps(preview, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        desk_bytes = len(json.dumps(desk, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        checks = {
            "import_preview": _metric(preview_times, 50),
            "tenant_summary": _metric(summary_times, 75),
            "acknowledge": _metric(acknowledge_times, 50),
            "preview_payload": {"bytes": preview_bytes, "budget_bytes": 20_000, "passed": preview_bytes <= 20_000},
            "summary_payload": {"bytes": desk_bytes, "budget_bytes": 30_000, "passed": desk_bytes <= 30_000},
            "initial_html": {"bytes": html_bytes, "budget_bytes": 100_000, "passed": html_bytes is None or html_bytes <= 100_000},
            "scan_provider_calls": {"count": scan["provider_call_count"], "budget": 0, "passed": scan["provider_call_count"] == 0},
        }
        return {
            "phase": "6K", "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "bounded_candidates": len(preview["candidates"]), "inbox_items": len(inbox),
            "rule_delivery": rule["delivery"], "checks": checks,
            "passed": all(row["passed"] for row in checks.values()),
            "caveat": "Local deterministic SQLite/contract benchmark; hosted database and network delivery were not exercised.",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-url", default=None)
    parser.add_argument("--output", default="review_workspace/phase6k_performance/summary.json")
    args = parser.parse_args()
    report = run(page_url=args.page_url)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
