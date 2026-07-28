from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.identity_tenancy import local_test_context
from lib.tenant_research_persistence import DeterministicFakeTenantResearchPersistence
from lib.tenant_research_sync import TenantResearchSyncCoordinator, build_reconciliation_plan
from scripts.benchmark_phase6k import run as run_phase6k


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def _sample(callback, count: int = 100) -> tuple[list[float], object]:
    durations: list[float] = []
    result = None
    for _ in range(count):
        started = time.perf_counter()
        result = callback()
        durations.append((time.perf_counter() - started) * 1_000)
    return durations, result


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


def _snapshot(*, changed: bool = False) -> dict:
    resources = []
    for index in range(25):
        payload = {
            "resource_id": f"watch-{index:02d}",
            "name": f"Research watch {index:02d}" + (" changed" if changed and index == 3 else ""),
            "version": 2 if changed and index < 5 else 1,
            "source_status": "cached" if index % 3 else "stale",
        }
        resources.append(
            {
                "resource_type": "watchlist",
                "resource_id": payload["resource_id"],
                "version": payload["version"],
                "deleted": False,
                "payload": payload,
            }
        )
    return {"snapshot_version": "tenant_research_sync.v1", "resources": resources, "resource_count": 25, "provider_call_count": 0}


def run(*, page_url: str | None = None, visual_summary: str | Path | None = None) -> dict:
    phase6k = run_phase6k(page_url=page_url)
    account_summary = dict(phase6k["checks"]["tenant_summary"])
    account_summary["budget_ms"] = 100
    account_summary["passed"] = float(account_summary["p95_ms"]) <= 100

    context = local_test_context("analyst-a")
    local = DeterministicFakeTenantResearchPersistence()
    local.seed(context, _snapshot(changed=True))
    remote = DeterministicFakeTenantResearchPersistence(available=False)
    with tempfile.TemporaryDirectory(prefix="global-terminal-phase6l-") as temporary:
        coordinator = TenantResearchSyncCoordinator(
            db_path=Path(temporary) / "sync.db",
            local=local,
            hosted=remote,
        )
        local_snapshot = local.snapshot(context)
        reconciliation_times, reconciliation = _sample(
            lambda: build_reconciliation_plan(local_snapshot, _snapshot(changed=False))
        )
        queued = coordinator.queue_first_sync(
            context,
            {"consent": True, "idempotency_key": "phase6l-performance-sync"},
        )
        status_times, status = _sample(lambda: coordinator.status(context))

    lazy_calls = None
    if visual_summary:
        visual_path = Path(visual_summary)
        if visual_path.exists():
            visual = json.loads(visual_path.read_text(encoding="utf-8"))
            lazy_calls = int(visual["captures"]["desktop"]["lazyAccountCalls"])

    checks = {
        "account_summary": account_summary,
        "sync_status": _metric(status_times, 100),
        "offline_reconciliation": _metric(reconciliation_times, 75),
        "sync_payload": {
            "bytes": int(queued["payload_bytes"]),
            "budget_bytes": 30_000,
            "resource_count": int(queued["resource_count"]),
            "resource_budget": 25,
            "passed": int(queued["payload_bytes"]) <= 30_000 and int(queued["resource_count"]) <= 25,
        },
        "initial_html": phase6k["checks"]["initial_html"],
        "hidden_account_requests": {
            "count": lazy_calls,
            "budget": 0,
            "passed": lazy_calls in {None, 0},
        },
        "sync_provider_calls": {
            "count": int(status["provider_call_count"]) + int(reconciliation["provider_call_count"]),
            "budget": 0,
            "passed": int(status["provider_call_count"]) + int(reconciliation["provider_call_count"]) == 0,
        },
    }
    return {
        "phase": "6L",
        "branch": "local-conformance",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": checks,
        "passed": all(row["passed"] for row in checks.values()),
        "bottleneck": "Hosted latency is unmeasured because no verified hosted adapter was available.",
        "caveat": "Deterministic local SQLite/fake-adapter benchmark; no hosted auth, RLS, or network sync was claimed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-url", default=None)
    parser.add_argument("--visual-summary", default="review_workspace/phase6l_visual/summary.json")
    parser.add_argument("--output", default="review_workspace/phase6l_performance/summary.json")
    args = parser.parse_args()
    report = run(page_url=args.page_url, visual_summary=args.visual_summary)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

