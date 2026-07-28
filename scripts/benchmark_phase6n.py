from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.attention_desk import build_attention_desk_contract, filter_and_rank_attention_items
from lib.identity_tenancy import local_test_context
from lib.watchlist_observation_runs import (
    ObservationRunStore,
    build_observation_run_plan,
    validate_observation_request,
)


NOW = datetime(2026, 7, 13, 14, 30, tzinfo=timezone.utc)
SYMBOLS = ("AAPL", "MSFT", "NVDA", "SPY", "QQQ")


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def _metric(values: list[float], budget_ms: float) -> dict:
    ordered = sorted(values)
    p95 = round(_p95(values), 3)
    return {
        "samples": len(values),
        "p50_ms": round(ordered[len(ordered) // 2], 3),
        "p95_ms": p95,
        "budget_ms": budget_ms,
        "passed": p95 <= budget_ms,
    }


def _watchlist(resource_id: str = "phase6n-benchmark") -> dict:
    return {
        "resource_id": resource_id,
        "name": "Phase 6N Benchmark",
        "items": [
            {"symbol": symbol, "asset_class": "etf" if symbol in {"SPY", "QQQ"} else "equity"}
            for symbol in SYMBOLS
        ],
    }


def _request(index: int, watchlist_id: str = "phase6n-benchmark") -> dict:
    return validate_observation_request(
        {
            "watchlist_id": watchlist_id,
            "idempotency_key": f"phase6n-benchmark-{index:05d}",
            "interval": "1d",
            "range": "3mo",
            "max_symbols": 5,
            "session_policy": "force-bounded",
        }
    )


def _snapshot(symbol: str, price: float, observed_at: datetime, retrieved_at: datetime) -> dict:
    observed = observed_at.isoformat()
    retrieved = retrieved_at.isoformat()
    return {
        "symbol": symbol,
        "identity": {"symbol": symbol, "asset_class": "etf" if symbol in {"SPY", "QQQ"} else "equity"},
        "quote": {
            "last_price": price,
            "change_percent": round((price % 7) - 3, 2),
            "market_data_as_of": observed,
            "provider": "benchmark-source",
            "source_url": f"https://example.test/quote/{symbol}",
        },
        "source_status": "cached",
        "observed_at": observed,
        "retrieved_at": retrieved,
        "fetched_at": retrieved,
        "source_register": [
            {
                "provider": "benchmark-source",
                "source_url": f"https://example.test/quote/{symbol}",
                "source_status": "cached",
                "observed_at": observed,
                "retrieved_at": retrieved,
            }
        ],
        "confidence": 0.8,
        "caveat": "Deterministic local benchmark; no provider request.",
        "data_gap": "Network and hosted database latency are excluded.",
        "not_financial_advice": True,
    }


def _result(index: int, when: datetime) -> dict:
    rows = [
        _snapshot(symbol, 100.0 + symbol_index + index * 0.25, when - timedelta(minutes=5), when)
        for symbol_index, symbol in enumerate(SYMBOLS)
    ]
    return {
        "rows": rows,
        "missing_capabilities": [],
        "provider_budget": {
            "maximum_calls": 16,
            "actual_calls": 0,
            "actual_calls_by_operation": {},
            "cache_hits": 5,
            "stale_hits": 0,
        },
        "provider_states": [
            {
                "provider": "benchmark-source",
                "operation": "snapshot",
                "configured": True,
                "contacted": False,
                "source_status": "cached",
            }
        ],
    }


def run(*, samples: int = 100) -> dict:
    sample_count = max(5, int(samples))
    context = local_test_context("analyst-a")
    watchlist = _watchlist()

    plan_times: list[float] = []
    for sample in range(sample_count):
        started = time.perf_counter()
        for batch in range(5):
            request = _request(sample * 5 + batch)
            build_observation_run_plan(context, watchlist, request, quota_usage={}, now=NOW)
        plan_times.append((time.perf_counter() - started) * 1_000)

    persist_times: list[float] = []
    compose_times: list[float] = []
    filter_times: list[float] = []
    latest_context: dict = {}
    latest_desk: dict = {}
    with tempfile.TemporaryDirectory(prefix="global-terminal-phase6n-") as temporary:
        store = ObservationRunStore(Path(temporary) / "observation.db")
        for sample in range(sample_count):
            when = NOW + timedelta(seconds=sample)
            request = _request(10_000 + sample)
            plan = build_observation_run_plan(context, watchlist, request, quota_usage={}, now=when)
            run_row = store.create_run(context, watchlist, request, plan, now=when)
            store.start_run(context, run_row["run_id"], now=when)
            started = time.perf_counter()
            store.commit_run(context, run_row["run_id"], _result(sample, when), now=when)
            persist_times.append((time.perf_counter() - started) * 1_000)

            latest_context = store.build_attention_context(context, now=when)
            started = time.perf_counter()
            latest_desk = build_attention_desk_contract(
                watchlist_changes=latest_context["changes"],
                observation_run=latest_context,
                mode="cache",
                now=when,
            )
            compose_times.append((time.perf_counter() - started) * 1_000)

            started = time.perf_counter()
            filter_and_rank_attention_items(latest_desk["all_items"], policy=latest_desk["policy"], now=when)
            filter_times.append((time.perf_counter() - started) * 1_000)

    run_summary = latest_context.get("latest_run") or {}
    payload_bytes = len(json.dumps(run_summary, ensure_ascii=False).encode("utf-8"))
    provider_calls = int(latest_context.get("provider_call_count") or 0) + int(latest_desk.get("provider_call_count") or 0)
    checks = {
        "plan_25_symbol_equivalent": _metric(plan_times, 50),
        "persist_diff_5_symbols": _metric(persist_times, 75),
        "attention_compose": _metric(compose_times, 75),
        "attention_filter_rank": _metric(filter_times, 50),
        "run_summary_payload": {
            "bytes": payload_bytes,
            "budget_bytes": 35_000,
            "passed": payload_bytes <= 35_000,
        },
        "provider_calls_during_triage": {
            "count": provider_calls,
            "budget": 0,
            "passed": provider_calls == 0,
        },
    }
    return {
        "phase": "6N",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "samples": sample_count,
        "product_run_symbol_cap": 5,
        "planning_equivalent_symbols": 25,
        "checks": checks,
        "passed": all(check["passed"] for check in checks.values()),
        "bottleneck": "Provider and hosted Supabase latency remain separate from this local contract benchmark.",
        "caveat": "The 25-symbol planning metric executes five independent five-symbol plans because the Phase 6N product hard cap is five symbols per explicit run.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--output", default="review_workspace/phase6n_performance/summary.json")
    args = parser.parse_args()
    report = run(samples=args.samples)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
