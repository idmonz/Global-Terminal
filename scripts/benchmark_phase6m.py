from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.attention_desk import AttentionReviewStore, build_attention_desk_contract, filter_and_rank_attention_items
from lib.identity_tenancy import local_test_context


NOW = datetime(2026, 7, 11, 0, 0, tzinfo=timezone.utc)


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def _sample(callback, count: int) -> tuple[list[float], object]:
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


def _stored_news_rows(count: int = 100) -> list[dict]:
    severities = ("critical", "high", "material", "info")
    statuses = ("live/fresh", "cached", "stale", "rate-limited")
    return [
        {
            "title": f"Stored evidence row {index:03d}",
            "summary": "A bounded source-linked observation is available for review.",
            "provider": f"provider-{index % 5}",
            "source_url": f"https://example.test/evidence/{index:03d}",
            "source_status": statuses[index % len(statuses)],
            "published_at": f"2026-07-10T{index % 24:02d}:{index % 60:02d}:00+00:00",
            "fetched_at": f"2026-07-10T{index % 24:02d}:{(index + 2) % 60:02d}:00+00:00",
            "confidence": round(0.6 + (index % 4) * 0.1, 2),
            "region": f"Region {index % 8}",
            "severity": severities[index % len(severities)],
            "caveat": "Stored evidence; not a live tick or recommendation.",
            "data_gap": "Independent confirmation may be absent.",
        }
        for index in range(count)
    ]


def _html_check(page_url: str | None) -> dict:
    if not page_url:
        return {
            "bytes": None,
            "budget_bytes": 100_000,
            "measured": False,
            "passed": True,
        }
    with urlopen(page_url, timeout=30) as response:  # noqa: S310 - explicit local product URL
        body = response.read()
    return {
        "bytes": len(body),
        "budget_bytes": 100_000,
        "measured": True,
        "passed": len(body) <= 100_000,
    }


def run(*, samples: int = 100, page_url: str | None = None, visual_summary: str | Path | None = None) -> dict:
    count = max(5, int(samples))
    news_rows = _stored_news_rows()
    compose_times, compose_result = _sample(
        lambda: build_attention_desk_contract(news_rows=news_rows, mode="fixture", now=NOW),
        count,
    )
    filter_policy = {
        "minimum_severity": "high",
        "included_change_kinds": ["new-evidence", "source-degradation", "stale-evidence"],
        "source_health_handling": "deprioritize",
        "version": 0,
    }
    filter_times, filter_result = _sample(
        lambda: filter_and_rank_attention_items(
            compose_result["all_items"],
            policy=filter_policy,
            now=NOW,
        ),
        count,
    )

    with tempfile.TemporaryDirectory(prefix="global-terminal-phase6m-") as temporary:
        store = AttentionReviewStore(Path(temporary) / "attention.db")
        context = local_test_context("analyst-a")
        store.list_states(context, ["f" * 64], now=NOW)
        mutation_index = 0

        def mutate() -> dict:
            nonlocal mutation_index
            fingerprint = f"{mutation_index:064x}"[-64:]
            mutation_index += 1
            return store.update_state(
                context,
                fingerprint,
                action="review",
                expected_version=0,
                now=NOW,
            )

        mutation_times, mutation_result = _sample(mutate, count)

    fixture = json.loads((ROOT / "static/api-fixtures/attention-desk.json").read_text(encoding="utf-8"))
    payload_bytes = len(json.dumps(fixture, ensure_ascii=False).encode("utf-8"))
    hidden_requests = None
    browser_provider_calls = None
    if visual_summary:
        visual_path = Path(visual_summary)
        if visual_path.exists():
            visual = json.loads(visual_path.read_text(encoding="utf-8"))
            desktop = visual.get("captures", {}).get("desktop", {})
            hidden_requests = int(desktop.get("hiddenRequestCount", 0))
            browser_provider_calls = int(desktop.get("providerRequestCount", 0))

    compose_provider_calls = int(compose_result.get("provider_call_count", -1))
    filtered_all, filtered_visible = filter_result
    filter_provider_calls = sum(int(row.get("provider_call_count", -1)) for row in filtered_all)
    provider_call_count = compose_provider_calls + filter_provider_calls + int(browser_provider_calls or 0)
    checks = {
        "compose_100_rows": _metric(compose_times, 75),
        "filter_rank_100_rows": _metric(filter_times, 50),
        "review_mutation": _metric(mutation_times, 50),
        "payload": {
            "bytes": payload_bytes,
            "budget_bytes": 50_000,
            "passed": payload_bytes <= 50_000,
        },
        "initial_html": _html_check(page_url),
        "hidden_account_requests": {
            "count": hidden_requests,
            "budget": 0,
            "measured": hidden_requests is not None,
            "passed": hidden_requests in {None, 0},
        },
        "provider_calls": {
            "count": provider_call_count,
            "budget": 0,
            "passed": provider_call_count == 0,
        },
    }
    return {
        "phase": "6M",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "row_count": 100,
        "visible_filtered_rows": len(filtered_visible),
        "last_review_state": mutation_result.get("review_state"),
        "checks": checks,
        "passed": all(check["passed"] for check in checks.values()),
        "bottleneck": "Hosted Supabase latency remains unmeasured because the reachable project has no Global Terminal schema and no admin deployment credential.",
        "caveat": "Local stored-evidence and SQLite benchmark; it does not claim provider, hosted database, or internet latency.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--page-url", default=None)
    parser.add_argument("--visual-summary", default="review_workspace/phase6m_visual/summary.json")
    parser.add_argument("--output", default="review_workspace/phase6m_performance/summary.json")
    args = parser.parse_args()
    report = run(samples=args.samples, page_url=args.page_url, visual_summary=args.visual_summary)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
