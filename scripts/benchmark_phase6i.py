from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _fetch(url: str, *, timeout: int = 60) -> tuple[int, int]:
    started = time.perf_counter()
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read()
    return int((time.perf_counter() - started) * 1_000_000), len(body)


def _percentile(values: list[int], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _measure(url: str, iterations: int) -> dict[str, float | int]:
    durations: list[int] = []
    payload_bytes = 0
    for _ in range(iterations):
        duration, payload_bytes = _fetch(url)
        durations.append(duration)
    return {
        "iterations": iterations,
        "payload_bytes": payload_bytes,
        "p50_ms": round(statistics.median(durations) / 1_000, 2),
        "p95_ms": round(_percentile(durations, 0.95) / 1_000, 2),
        "maximum_ms": round(max(durations) / 1_000, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8061")
    parser.add_argument("--web-base", default="http://127.0.0.1:3061")
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument(
        "--output",
        default="review_workspace/phase6i_performance/summary.json",
    )
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
    chart_query = urlencode(
        {
            "asset_class": "equity",
            "interval": "1d",
            "range": "3mo",
            "runtime_mode": "cache",
        }
    )
    operations_url = (
        f"{args.api_base.rstrip('/')}/api/analyst-workspace/AAPL/operations"
        f"?{operations_query}"
    )
    chart_url = (
        f"{args.api_base.rstrip('/')}/api/symbol-workstation/AAPL/panels/"
        f"chart-core?{chart_query}"
    )
    web_url = (
        f"{args.web_base.rstrip('/')}/?view=analyst-workspace"
        "&mode=cache&symbol=AAPL&assetClass=equity"
        "&interval=1d&range=3mo&layout=research&panel=chart-core"
    )
    report = {
        "operations": _measure(operations_url, iterations),
        "cached_chart_core": _measure(chart_url, iterations),
        "initial_analyst_html": _measure(web_url, 1),
        "budgets": {
            "operations_payload_bytes": 30_000,
            "operations_p95_ms": 100,
            "cached_panel_p95_ms": 250,
            "initial_analyst_html_bytes": 100_000,
        },
        "provider_calls": 0,
        "not_financial_advice": True,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
