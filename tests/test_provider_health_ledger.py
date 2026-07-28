from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lib.data_status import DataResult
from lib.provider_health_engine import build_provider_health_ledger, classify_provider_ledger_status, summarize_provider_health_ledger


def _result(**overrides):
    base = {
        "ok": True,
        "data": [{"row": 1}],
        "source": "unit",
        "provider": "unit",
        "fetched_at": datetime.now(timezone.utc),
        "stale_after_seconds": 60,
        "coverage": "1 row",
    }
    base.update(overrides)
    return DataResult(**base)


def test_provider_health_ledger_classifies_runtime_states():
    cases = {
        "live/fresh": _result(),
        "cached": _result(is_cached=True),
        "stale": _result(is_cached=True, fetched_at=datetime.now(timezone.utc) - timedelta(hours=2), warning="Live fetch failed; using stale cache."),
        "rate-limited": _result(ok=False, error="429 rate limited", warning="No cached fallback is available."),
        "forbidden/subscription-blocked": _result(ok=False, error="403 forbidden or subscription required"),
        "missing-key": _result(ok=False, error="Missing optional environment variable: NEWSAPI_KEY", is_paid_required=True),
        "proxy/static": _result(source="static chokepoint registry", provider="local", is_estimated=True),
        "unavailable": _result(ok=False, error="timeout"),
    }
    for expected, result in cases.items():
        assert classify_provider_ledger_status(result) == expected


def test_provider_health_ledger_summarizes_partial_success():
    fresh = _result(provider="rss", source="public RSS", data=[{"title": "ok"}, {"title": "ok2"}])
    rate_limited = _result(ok=False, provider="gdelt", source="GDELT", error="HTTP 429 rate limited")
    forbidden = _result(ok=False, provider="opec_rss", source="OPEC RSS", error="HTTP 403 forbidden")

    ledger = build_provider_health_ledger([fresh, rate_limited, forbidden])
    summary = summarize_provider_health_ledger(ledger)

    assert ledger[0]["row_count"] == 2
    assert {row["status"] for row in ledger} == {"live/fresh", "rate-limited", "forbidden/subscription-blocked"}
    assert summary["ledger_status"] == "partial_success"
    assert summary["available_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["limited_count"] == 1
