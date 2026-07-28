from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.identity_tenancy import local_test_context
from lib.research_workspace_db import execute_query, json_dumps
from lib.watchlist_alert_manager import WatchlistAlertManagerStore, build_watchlist_alert_manager_contract


BASE_TIME = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)
SYMBOLS = ("AAPL", "MSFT", "NVDA", "SPY", "GLD")


def _milliseconds(operation: Callable[[], Any]) -> float:
    started = time.perf_counter()
    operation()
    return (time.perf_counter() - started) * 1_000


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)] if ordered else 0.0


def _seed(db_path: Path) -> tuple[dict[str, Any], WatchlistAlertManagerStore]:
    context = local_test_context("analyst-a")
    tenant_id = context["tenant_id"]
    user_id = context["user_id"]
    watchlist_id = "twl_phase6o_benchmark"
    run_id = "obsrun_phase6o_benchmark"
    timestamp = BASE_TIME.isoformat()
    execute_query(
        "INSERT INTO tenant_watchlists (resource_id, tenant_id, owner_user_id, name, source_key, source_fingerprint, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
        (watchlist_id, tenant_id, user_id, "Phase 6O Benchmark", "phase6o-benchmark", "phase6o-benchmark-fingerprint", timestamp, timestamp),
        db_path=db_path,
    )
    for position, symbol in enumerate(SYMBOLS):
        execute_query(
            "INSERT INTO tenant_watchlist_items (resource_id, tenant_id, watchlist_resource_id, symbol, asset_class, display_name, exchange, position, provider, source_url, source_status, observed_at, retrieved_at, evidence_json, version, active, created_at, updated_at) VALUES (?, ?, ?, ?, 'equity', ?, 'NASDAQ', ?, 'phase6o.benchmark', '', 'fresh', ?, ?, '{}', 1, 1, ?, ?)",
            (f"twi_phase6o_bench_{position}", tenant_id, watchlist_id, symbol, symbol, position, timestamp, timestamp, timestamp, timestamp),
            db_path=db_path,
        )
    execute_query(
        "INSERT INTO tenant_observation_runs (run_id, tenant_id, owner_user_id, watchlist_resource_id, watchlist_name, idempotency_key, request_fingerprint, status, requested_symbols_json, requested_count, completed_count, provider_call_budget, provider_call_count, diff_json, retrieved_at, completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?, 5, 5, 0, 0, '{}', ?, ?, ?, ?)",
        (run_id, tenant_id, user_id, watchlist_id, "Phase 6O Benchmark", "phase6o-benchmark-observation", "phase6o-benchmark-request", json_dumps(SYMBOLS), timestamp, timestamp, timestamp, timestamp),
        db_path=db_path,
    )
    for position, symbol in enumerate(SYMBOLS):
        price = 150.0 + position
        payload = {"symbol": symbol, "quote": {"last_price": price, "change_pct": 1.5, "source_status": "fresh"}}
        execute_query(
            "INSERT INTO tenant_observation_snapshots (snapshot_id, tenant_id, owner_user_id, run_id, watchlist_resource_id, symbol, asset_class, snapshot_status, source_status, observed_at, retrieved_at, provider, source_url, confidence, content_hash, payload_json, caveat, data_gap, created_at) VALUES (?, ?, ?, ?, ?, ?, 'equity', 'fresh', 'fresh', ?, ?, 'phase6o.benchmark', '', 1.0, ?, ?, '', '', ?)",
            (f"obssnap_phase6o_bench_{position}", tenant_id, user_id, run_id, watchlist_id, symbol, timestamp, timestamp, f"phase6o-hash-{position}", json_dumps(payload), timestamp),
            db_path=db_path,
        )
    store = WatchlistAlertManagerStore(db_path)
    for symbol in SYMBOLS:
        store.create_rule(
            context,
            {
                "watchlist_id": watchlist_id,
                "symbol": symbol,
                "rule_type": "price_above",
                "threshold": 100,
                "threshold_unit": "USD",
                "frequency": "5m",
                "session_policy": "market-aware",
                "cooldown_minutes": 60,
                "expires_at": (BASE_TIME + timedelta(days=7)).isoformat(),
                "severity": "watch",
                "expected_version": 0,
            },
            now=BASE_TIME,
        )
    return context, store


def run_benchmark(*, samples: int = 50, db_path: Path | None = None) -> dict[str, Any]:
    owned_temp: tempfile.TemporaryDirectory[str] | None = None
    if db_path is None:
        owned_temp = tempfile.TemporaryDirectory(prefix="global-terminal-phase6o-")
        db_path = Path(owned_temp.name) / "benchmark.db"
    try:
        context, store = _seed(db_path)
        store.plan_due(context, now=BASE_TIME)
        cold_evaluation_ms = _milliseconds(
            lambda: store.evaluate_due(
                context,
                {"idempotency_key": "phase6o-benchmark-cold", "mode": "manual"},
                now=BASE_TIME,
            )
        )
        plan_samples = [_milliseconds(lambda: store.plan_due(context, now=BASE_TIME)) for _ in range(samples)]
        evaluation_samples: list[float] = []
        for index in range(samples):
            current = BASE_TIME + timedelta(minutes=5 * index)
            execute_query(
                "UPDATE tenant_watchlist_alert_rules SET next_due_at=? WHERE tenant_id=? AND state='active'",
                (current.isoformat(), context["tenant_id"]),
                db_path=db_path,
            )
            evaluation_samples.append(
                _milliseconds(
                    lambda index=index, current=current: store.evaluate_due(
                        context,
                        {"idempotency_key": f"phase6o-benchmark-{index:04d}", "mode": "manual"},
                        now=current,
                    )
                )
            )
        read_samples = [_milliseconds(lambda: (store.list_rules(context), store.list_triggers(context), store.list_evaluations(context))) for _ in range(samples)]
        contract = build_watchlist_alert_manager_contract(context, store=store, now=BASE_TIME + timedelta(hours=4))
        payload_bytes = len(json.dumps(contract, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))
        results = {
            "evidence_version": "phase6o.performance.v1",
            "symbol_count": len(SYMBOLS),
            "samples": samples,
            "cold_evaluation_ms": round(cold_evaluation_ms, 3),
            "due_plan_p95_ms": round(_p95(plan_samples), 3),
            "evaluation_p95_ms": round(_p95(evaluation_samples), 3),
            "read_p95_ms": round(_p95(read_samples), 3),
            "payload_bytes": payload_bytes,
            "provider_call_count": sum(int(row.get("provider_call_count") or 0) for row in contract.get("evaluations", [])),
            "thresholds": {"due_plan_p95_ms": 75, "evaluation_p95_ms": 75, "read_p95_ms": 75, "payload_bytes": 100_000},
        }
        results["passed"] = (
            results["due_plan_p95_ms"] < 75
            and results["evaluation_p95_ms"] < 75
            and results["read_p95_ms"] < 75
            and results["payload_bytes"] < 100_000
            and results["provider_call_count"] == 0
        )
        return results
    finally:
        if owned_temp is not None:
            owned_temp.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the bounded Phase 6O Alert Manager path.")
    parser.add_argument("--samples", type=int, default=50)
    parser.add_argument("--output", default="review_workspace/phase6o_performance.json")
    args = parser.parse_args()
    result = run_benchmark(samples=max(5, min(args.samples, 100)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
