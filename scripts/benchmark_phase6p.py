from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.account_continuity import AccountBundleStore, AccountContinuityCoordinator
from lib.research_workspace_db import execute_query


CONTEXT = {
    "state": "authenticated-hosted",
    "authenticated": True,
    "identity_provider": "supabase",
    "user_id": "33333333-3333-4333-8333-333333333333",
    "tenant_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    "role": "owner",
    "_supabase_access_token": "synthetic-benchmark-token",
}


class BenchmarkRepository:
    def health(self) -> dict[str, Any]:
        return {
            "provider": "supabase",
            "configured": True,
            "contacted": False,
            "hosted_verified": False,
            "source_status": "benchmark-local",
            "provider_call_count": 0,
        }

    def load(self, context: dict[str, Any]) -> None:
        del context
        return None

    def save(self, context: dict[str, Any], bundle: dict[str, Any], *, expected_version: int, idempotency_key: str) -> dict[str, Any]:
        del context, bundle, idempotency_key
        return {"status": "applied", "version": expected_version + 1, "fingerprint": ""}

    def delete(self, context: dict[str, Any], *, expected_version: int, idempotency_key: str) -> dict[str, Any]:
        del context, idempotency_key
        return {"status": "deleted", "version": expected_version + 1}


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def _sample(callback, count: int) -> tuple[list[float], Any]:
    durations: list[float] = []
    result = None
    for _ in range(count):
        started = time.perf_counter()
        result = callback()
        durations.append((time.perf_counter() - started) * 1_000)
    return durations, result


def _metric(values: list[float], budget_ms: float) -> dict[str, Any]:
    ordered = sorted(values)
    p95 = round(_p95(values), 3)
    return {
        "samples": len(values),
        "p50_ms": round(ordered[len(ordered) // 2], 3),
        "p95_ms": p95,
        "budget_ms": budget_ms,
        "passed": p95 <= budget_ms,
    }


def _seed(db_path: Path, rows: int = 100) -> None:
    now = "2026-07-15T09:00:00+00:00"
    for index in range(rows):
        execute_query(
            """
            INSERT INTO tenant_workspace_preferences (
              resource_id, tenant_id, owner_user_id, preference_key,
              value_json, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                f"twp_phase6p_{index:03d}",
                CONTEXT["tenant_id"],
                CONTEXT["user_id"],
                f"benchmark-{index:03d}",
                json.dumps({"panel": index, "visible": index % 2 == 0}, separators=(",", ":")),
                now,
                now,
            ),
            db_path=db_path,
        )


def run(*, samples: int = 30) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="global-terminal-phase6p-") as temporary:
        root = Path(temporary)
        source_db = root / "source.db"
        target_db = root / "target.db"
        _seed(source_db)
        source = AccountBundleStore(source_db)
        capture_times, bundle = _sample(lambda: source.capture(CONTEXT), max(5, samples))
        target = AccountBundleStore(target_db)
        target.restore(CONTEXT, bundle, prefer_remote=True)
        restore_times, restored = _sample(
            lambda: target.restore(CONTEXT, bundle),
            max(5, samples),
        )
        coordinator = AccountContinuityCoordinator(
            target_db,
            repository=BenchmarkRepository(),
            enabled=True,
        )
        status_times, status = _sample(lambda: coordinator.status(CONTEXT), max(5, samples))

    checks = {
        "capture_100_rows": _metric(capture_times, 100),
        "restore_100_rows": _metric(restore_times, 175),
        "continuity_status": _metric(status_times, 50),
        "account_bundle": {
            "rows": int(bundle["row_count"]),
            "bytes": int(bundle["payload_bytes"]),
            "row_budget": 1_000,
            "byte_budget": 512_000,
            "passed": int(bundle["row_count"]) == 100 and int(bundle["payload_bytes"]) <= 512_000,
        },
        "restore_integrity": {
            "conflict_count": int(restored["conflict_count"]),
            "provider_calls": int(status["provider_call_count"]),
            "passed": int(restored["conflict_count"]) == 0 and int(status["provider_call_count"]) == 0,
        },
    }
    return {
        "phase": "6P",
        "branch": "local-account-continuity-conformance",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": checks,
        "passed": all(check["passed"] for check in checks.values()),
        "bottleneck": "Hosted auth and PostgREST latency require the secure owner-run A/B journey.",
        "caveat": "Local SQLite serialization and restore benchmark; no hosted network latency is claimed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", default="review_workspace/phase6p_performance/summary.json")
    args = parser.parse_args()
    report = run(samples=max(5, min(args.samples, 100)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
