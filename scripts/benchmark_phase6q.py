from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) * percentile + 0.999999) - 1)))
    return round(ordered[index], 3)


def main() -> int:
    from lib.hosted_scheduler_operations import HostedSchedulerStore
    from lib.identity_tenancy import local_test_context

    samples = 200
    context = local_test_context("analyst-a")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with tempfile.TemporaryDirectory(prefix="global-terminal-phase6q-benchmark-") as temporary:
        store = HostedSchedulerStore(Path(temporary) / "scheduler.db")
        store.build_contract(context, now=now)
        read_ms: list[float] = []
        claim_ms: list[float] = []
        for _ in range(samples):
            started = time.perf_counter()
            payload = store.build_contract(context, now=now)
            read_ms.append((time.perf_counter() - started) * 1_000)
            if payload["summary"]["provider_call_count"] != 0:
                raise RuntimeError("Scheduler read benchmark contacted a provider.")

            started = time.perf_counter()
            claim = store.claim_due("phase6q-benchmark", now=now)
            claim_ms.append((time.perf_counter() - started) * 1_000)
            if claim.get("provider_call_count") != 0 or claim.get("status") != "disabled":
                raise RuntimeError("Safe-default claim benchmark crossed its boundary.")

    report = {
        "evidence_version": "phase6q.performance.v1",
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sample_count": samples,
        "scheduler_read_compose": {
            "p50_ms": _percentile(read_ms, 0.50),
            "p95_ms": _percentile(read_ms, 0.95),
            "mean_ms": round(statistics.fmean(read_ms), 3),
            "limit_p95_ms": 75.0,
        },
        "safe_default_claim": {
            "p50_ms": _percentile(claim_ms, 0.50),
            "p95_ms": _percentile(claim_ms, 0.95),
            "mean_ms": round(statistics.fmean(claim_ms), 3),
        },
        "provider_call_count": 0,
        "identifiers_redacted": True,
        "secrets_printed": False,
    }
    report["passed"] = report["scheduler_read_compose"]["p95_ms"] < report["scheduler_read_compose"]["limit_p95_ms"]
    output = ROOT / "review_workspace" / "phase6q_performance_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
