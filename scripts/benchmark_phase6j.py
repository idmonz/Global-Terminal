from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.api_contracts import build_api_account_workspace_payload
from lib.identity_tenancy import SQLiteTenantPreferenceAdapter, anonymous_context, local_test_context


def _percentile(values: list[int], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _summary(durations: list[int], payload_bytes: int, iterations: int) -> dict[str, float | int]:
    return {
        "iterations": iterations,
        "payload_bytes": payload_bytes,
        "p50_ms": round(statistics.median(durations) / 1_000, 2),
        "p95_ms": round(_percentile(durations, 0.95) / 1_000, 2),
        "maximum_ms": round(max(durations) / 1_000, 2),
    }


def _measure_http(url: str, iterations: int) -> dict[str, float | int]:
    durations: list[int] = []
    payload_bytes = 0
    for _ in range(iterations):
        started = time.perf_counter_ns()
        with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=60) as response:
            body = response.read()
        durations.append((time.perf_counter_ns() - started) // 1_000)
        payload_bytes = len(body)
    return _summary(durations, payload_bytes, iterations)


def _measure_local_preferences(iterations: int) -> dict[str, float | int]:
    durations: list[int] = []
    payload_bytes = 0
    with tempfile.TemporaryDirectory(prefix="global-terminal-phase6j-") as directory:
        adapter = SQLiteTenantPreferenceAdapter(Path(directory) / "tenant.db")
        context = local_test_context("analyst-a")
        version = 0
        for index in range(iterations):
            started = time.perf_counter_ns()
            saved = adapter.save(
                context,
                "analyst-layout",
                {
                    "preset": "research",
                    "splitPercent": 50 + (index % 20),
                    "focusedPanel": "chart-core",
                    "visiblePanels": ["chart-core", "financials", "catalysts", "sources"],
                },
                expected_version=version,
            )
            restored = adapter.get(context, "analyst-layout")
            durations.append((time.perf_counter_ns() - started) // 1_000)
            version = int(saved["version"])
            payload_bytes = len(json.dumps(restored, separators=(",", ":")).encode("utf-8"))
    return _summary(durations, payload_bytes, iterations)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8062")
    parser.add_argument("--web-base", default="http://127.0.0.1:3062")
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--output", default="review_workspace/phase6j_performance/summary.json")
    args = parser.parse_args()
    iterations = max(5, min(args.iterations, 100))

    operations_query = urlencode(
        {
            "asset_class": "equity",
            "interval": "1d",
            "range": "3mo",
            "panels": "chart-core,financials,catalysts,sources",
        }
    )
    account_contract = build_api_account_workspace_payload(anonymous_context())
    account_contract_bytes = len(
        json.dumps(account_contract, separators=(",", ":")).encode("utf-8")
    )
    report = {
        "account_contract": {"payload_bytes": account_contract_bytes, "provider_calls": 0},
        "anonymous_session_http": _measure_http(
            f"{args.api_base.rstrip('/')}/api/account/session", iterations
        ),
        "tenant_preference_roundtrip": _measure_local_preferences(iterations),
        "phase6i_operations_regression": _measure_http(
            f"{args.api_base.rstrip('/')}/api/analyst-workspace/AAPL/operations?{operations_query}",
            iterations,
        ),
        "initial_analyst_html": _measure_http(
            f"{args.web_base.rstrip('/')}/?view=analyst-workspace&mode=fixture&symbol=AAPL",
            1,
        ),
        "budgets": {
            "account_contract_bytes": 12_000,
            "anonymous_session_p95_ms": 100,
            "tenant_preference_p95_ms": 50,
            "phase6i_operations_bytes": 30_000,
            "phase6i_operations_p95_ms": 100,
            "initial_analyst_html_bytes": 100_000,
        },
        "hosted_provider_contacted": False,
        "not_financial_advice": True,
    }
    budgets = report["budgets"]
    checks = {
        "account_contract_bytes": account_contract_bytes <= budgets["account_contract_bytes"],
        "anonymous_session_p95_ms": report["anonymous_session_http"]["p95_ms"] <= budgets["anonymous_session_p95_ms"],
        "tenant_preference_p95_ms": report["tenant_preference_roundtrip"]["p95_ms"] <= budgets["tenant_preference_p95_ms"],
        "phase6i_operations_bytes": report["phase6i_operations_regression"]["payload_bytes"] <= budgets["phase6i_operations_bytes"],
        "phase6i_operations_p95_ms": report["phase6i_operations_regression"]["p95_ms"] <= budgets["phase6i_operations_p95_ms"],
        "initial_analyst_html_bytes": report["initial_analyst_html"]["payload_bytes"] <= budgets["initial_analyst_html_bytes"],
    }
    report["checks"] = checks
    report["ok"] = all(checks.values())

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
