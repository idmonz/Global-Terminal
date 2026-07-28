from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.api.app import create_app


DEFAULT_OUTPUT = ROOT / "review_workspace" / "phase6h_performance" / "summary.json"
ROUTES = {
    "workspace_manifest": "/api/analyst-workspace/AAPL?asset_class=equity&runtime_mode=fixture",
    "chart_core": "/api/symbol-workstation/AAPL/panels/chart-core?asset_class=equity&runtime_mode=fixture",
    "financials": "/api/symbol-workstation/AAPL/panels/financials?asset_class=equity&runtime_mode=fixture",
    "catalysts": "/api/symbol-workstation/AAPL/panels/catalysts?asset_class=equity&runtime_mode=fixture",
    "sources": "/api/symbol-workstation/AAPL/panels/sources?asset_class=equity&runtime_mode=fixture",
}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * fraction) - 1))
    return ordered[index]


def benchmark(iterations: int = 25) -> dict[str, Any]:
    client = TestClient(create_app())
    results: dict[str, Any] = {}
    for name, route in ROUTES.items():
        samples: list[float] = []
        sizes: list[int] = []
        etag = None
        for _ in range(iterations):
            started = time.perf_counter()
            response = client.get(route)
            samples.append((time.perf_counter() - started) * 1000)
            sizes.append(len(response.content))
            if response.status_code != 200:
                raise RuntimeError(f"{name} returned HTTP {response.status_code}")
            etag = response.headers.get("etag")
        conditional = client.get(route, headers={"If-None-Match": etag or ""})
        results[name] = {
            "iterations": iterations,
            "p50_ms": round(statistics.median(samples), 3),
            "p95_ms": round(percentile(samples, 0.95), 3),
            "maximum_bytes": max(sizes),
            "etag_304": conditional.status_code == 304,
        }
    visual_path = ROOT / "review_workspace" / "phase6h_visual" / "summary.json"
    visual = json.loads(visual_path.read_text(encoding="utf-8")) if visual_path.exists() else {}
    desktop = ((visual.get("captures") or {}).get("desktop") or {})
    results["browser"] = {
        "initial_html_bytes": desktop.get("htmlBytes"),
        "background_rsc_prefetches": desktop.get("rscRequests"),
        "desktop_panel_request_count": len(desktop.get("panelRequests") or []),
        "mobile_requests_before_action": len(
            (((visual.get("captures") or {}).get("mobile") or {}).get("requestsBeforeAction") or [])
        ),
    }
    return {
        "benchmark": "phase6h.synchronized-analyst-workspace",
        "fixture_only": True,
        "provider_calls": 0,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = benchmark(max(5, min(args.iterations, 200)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
