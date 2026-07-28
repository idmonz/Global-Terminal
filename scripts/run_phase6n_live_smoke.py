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

from lib.attention_desk import build_attention_desk_contract
from lib.config import get_settings
from lib.identity_tenancy import local_test_context
from lib.watchlist_observation_runs import ObservationRunCoordinator, ObservationRunStore


class ControlledOfflineAdapter:
    def observe(self, watchlist, plan, *, previous_rows, cancellation_requested):
        del watchlist, previous_rows, cancellation_requested
        symbols = list(plan.get("requested_symbols") or [])
        return {
            "rows": [],
            "missing_capabilities": [
                {
                    "symbol": symbol,
                    "provider": "controlled-offline",
                    "capability": "history",
                    "source_status": "unavailable",
                    "reason": "controlled-provider-offline",
                }
                for symbol in symbols
            ],
            "provider_budget": {
                "maximum_calls": 16,
                "actual_calls": 0,
                "actual_calls_by_operation": {},
                "cache_hits": 0,
                "stale_hits": 0,
            },
            "provider_states": [
                {
                    "provider": "controlled-offline",
                    "operation": "history",
                    "configured": True,
                    "contacted": False,
                    "source_status": "unavailable",
                }
            ],
        }


def _request(day: str, suffix: str, policy: str) -> dict[str, Any]:
    return {
        "watchlist_id": "phase6n-live-aapl",
        "idempotency_key": f"phase6n-live-{day}-{suffix}",
        "interval": "1d",
        "range": "3mo",
        "max_symbols": 1,
        "session_policy": policy,
    }


def _public_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        key: run.get(key)
        for key in (
            "run_id",
            "status",
            "requested_count",
            "completed_count",
            "failed_count",
            "lkg_reused_count",
            "provider_call_budget",
            "provider_call_count",
            "provider_budget",
            "provider_states",
            "missing_capabilities",
            "attempted_at",
            "retrieved_at",
            "completed_at",
            "duration_ms",
            "error_code",
            "idempotent_replay",
        )
    }


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "phase6n-live.db"
    report_path = output_dir / "summary.json"
    context = local_test_context("analyst-a")
    store = ObservationRunStore(db_path)
    watchlist = {
        "resource_id": "phase6n-live-aapl",
        "name": "Phase 6N AAPL Live QA",
        "items": [{"symbol": "AAPL", "asset_class": "equity"}],
    }
    loader = lambda _context, resource_id: watchlist if resource_id == watchlist["resource_id"] else None
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    coordinator = ObservationRunCoordinator(store, loader, execute_inline=True)

    quota_before = store.quota_usage(context)
    live_run = coordinator.submit(context, _request(day, "source-backed", "force-bounded"))
    quota_after_live = store.quota_usage(context)
    live_snapshots = store.list_snapshots(context, str(live_run.get("run_id") or ""))

    replay = coordinator.submit(context, _request(day, "source-backed", "force-bounded"))
    quota_after_replay = store.quota_usage(context)

    cache_run = coordinator.submit(context, _request(day, "cache-only-v2", "cache-only"))
    quota_after_cache = store.quota_usage(context)

    offline = ObservationRunCoordinator(store, loader, adapter=ControlledOfflineAdapter(), execute_inline=True)
    offline_run = offline.submit(context, _request(day, "controlled-offline-v2", "force-bounded"))
    quota_after_offline = store.quota_usage(context)
    offline_snapshots = store.list_snapshots(context, str(offline_run.get("run_id") or ""))

    attention_context = store.build_attention_context(context)
    attention = build_attention_desk_contract(
        watchlist_changes=attention_context.get("changes") or [],
        observation_run=attention_context,
        mode="cache",
    )
    second_read = store.build_attention_context(context)
    settings = get_settings()

    report = {
        "phase": "6N",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "database": db_path.name,
        "configured_keys": {
            "ALPHAVANTAGE_API_KEY": bool(settings.alphavantage_api_key),
            "FINNHUB_API_KEY": bool(settings.finnhub_api_key),
        },
        "source_backed_run": _public_run(live_run),
        "source_backed_snapshots": [
            {
                "symbol": row.get("symbol"),
                "source_status": row.get("source_status"),
                "provider": row.get("provider"),
                "source_url": row.get("source_url"),
                "observed_at": row.get("observed_at"),
                "retrieved_at": row.get("retrieved_at"),
                "last_price": (row.get("payload") or {}).get("quote", {}).get("last_price"),
                "lkg_reused": bool(row.get("lkg_source_snapshot_id")),
            }
            for row in live_snapshots
        ],
        "same_day_replay": {
            "run_id": replay.get("run_id"),
            "idempotent_replay": replay.get("idempotent_replay"),
            "additional_quota_calls": {
                key: quota_after_replay.get(key, 0) - quota_after_live.get(key, 0)
                for key in quota_after_replay
            },
        },
        "cache_only_run": _public_run(cache_run),
        "controlled_offline_run": _public_run(offline_run),
        "controlled_offline_snapshots": [
            {
                "symbol": row.get("symbol"),
                "source_status": row.get("source_status"),
                "observed_at": row.get("observed_at"),
                "retrieved_at": row.get("retrieved_at"),
                "lkg_reused": bool(row.get("lkg_source_snapshot_id")),
            }
            for row in offline_snapshots
        ],
        "quota_ledger": {
            "before": quota_before,
            "after_source_backed": quota_after_live,
            "after_replay": quota_after_replay,
            "after_cache_only": quota_after_cache,
            "after_controlled_offline": quota_after_offline,
        },
        "attention_zero_call_proof": {
            "first_read_provider_calls": attention_context.get("provider_call_count"),
            "second_read_provider_calls": second_read.get("provider_call_count"),
            "compose_provider_calls": attention.get("summary", {}).get("provider_call_count"),
            "material_change_count": attention_context.get("material_change_count"),
        },
        "private_values_included": False,
        "caveat": "One bounded source-backed AAPL run; same-day reruns are idempotent. A successful response is not a guarantee of general provider availability or exchange-real-time data.",
        "not_financial_advice": True,
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    for forbidden in ("apikey=", "token=", "authorization", "bearer ", "sk-"):
        if forbidden in encoded.lower():
            raise RuntimeError("Sanitized live report contains a forbidden credential marker.")
    report_path.write_text(encoded, encoding="utf-8")
    return {**report, "report_file": str(report_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one idempotent, bounded Phase 6N source-backed smoke.")
    parser.add_argument("--output-dir", default="review_workspace/phase6n_live")
    args = parser.parse_args()
    print(json.dumps(run(Path(args.output_dir)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
