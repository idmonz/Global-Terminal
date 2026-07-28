from __future__ import annotations

import json

from lib.api_contracts import build_api_daily_brief_payload, validate_api_payload
from lib.daily_briefing import build_daily_brief_contract


def _depth_inputs() -> dict:
    base = {
        "provider": "phase5r-test-provider",
        "source": "Phase 5R observed test source",
        "source_url": "https://example.test/phase5r/source",
        "fetched_at": "2026-06-23T02:00:00+00:00",
        "freshness": "live/fresh",
        "source_status": "live/fresh",
        "confidence": 0.84,
        "caveat": "Test source-bound observation.",
        "data_gap": "No paid entitlement in this test.",
    }
    market_rows = [
        {**base, "symbol": "SPY", "label": "S&P 500 ETF", "last_price": 550.0, "daily_return_pct": 0.72, "one_month_return_pct": 2.4},
        {**base, "symbol": "TLT", "label": "US duration proxy", "last_price": 92.0, "daily_return_pct": -0.35, "one_month_return_pct": -1.7},
    ]
    return {
        "market": {
            "market_tape": market_rows,
            "chart_specs": [
                {
                    **base,
                    "chart_id": "phase5r.cross_asset",
                    "chart_type": "bar",
                    "title": "Phase 5R Cross Asset Test Chart",
                    "unit": "percent",
                    "series": [{"name": "daily return", "points": [{"x": "SPY", "y": 0.72}, {"x": "TLT", "y": -0.35}]}],
                    "data_gap": "Chart is built only from the referenced market rows.",
                }
            ],
        },
        "war_map": {
            "markers": [
                {
                    **base,
                    "marker_id": "phase5r-event-one",
                    "title": "Observed shipping pressure",
                    "region": "Red Sea",
                    "severity": "elevated",
                    "severity_score": 75,
                    "timestamp": "2026-06-23T01:45:00+00:00",
                    "related_asset_node_ids": ["commodity:brent"],
                }
            ]
        },
        "news": {
            "normalized_news": [
                {
                    **base,
                    "title": "Public report describes a logistics update",
                    "region": "Europe",
                    "published_at": "2026-06-23T01:50:00+00:00",
                    "related_assets": ["EURUSD"],
                }
            ]
        },
        "provider_rows": [
            {
                "provider": "opensky",
                "source": "OpenSky OAuth",
                "status": "missing-key",
                "source_status": "missing-key",
                "availability": "unavailable",
                "confidence": 0.0,
                "caveat": "Flight layer is not claimed live.",
                "data_gap": "No successful states fetch is attached.",
            }
        ],
        "watchlists": [],
    }


def test_phase5r_daily_brief_adds_source_bound_chart_panels_and_perspectives():
    brief = build_daily_brief_contract(
        **_depth_inputs(),
        period="morning",
        runtime_mode="live-if-available",
        generated_at="2026-06-23T02:05:00+00:00",
    )
    source_ids = {row["source_id"] for row in brief["source_register"]}
    claim_ids = {row["claim_id"] for row in brief["claims"]}

    assert brief["chart_panels"]
    assert brief["research_perspectives"]
    assert brief["coverage"]["chart_panel_count"] == len(brief["chart_panels"])
    assert brief["coverage"]["research_perspective_count"] == len(brief["research_perspectives"])
    assert all(set(row["source_ids"]) <= source_ids for row in brief["chart_panels"])
    assert all(set(row["claim_ids"]) <= claim_ids for row in brief["chart_panels"])
    assert all(row["point_count"] > 0 for row in brief["chart_panels"])
    assert all(set(row["source_ids"]) <= source_ids for row in brief["research_perspectives"])
    assert all(set(row["claim_ids"]) <= claim_ids for row in brief["research_perspectives"])
    assert all(row["not_financial_advice"] is True for row in brief["research_perspectives"])
    assert brief["validation"]["valid"] is True, brief["validation"]["issues"]


def test_phase5r_daily_brief_api_summary_and_secret_scan_stay_safe():
    envelope = build_api_daily_brief_payload(
        brief=build_daily_brief_contract(
            **_depth_inputs(),
            period="morning",
            runtime_mode="live-if-available",
            generated_at="2026-06-23T02:05:00+00:00",
        )
    )
    valid, issues = validate_api_payload(envelope)
    assert valid, issues
    assert envelope["summary"]["chart_panel_count"] >= 1
    assert envelope["summary"]["research_perspective_count"] >= 1
    encoded = json.dumps(envelope, sort_keys=True)
    assert "AIza" not in encoded
    assert "sk-" not in encoded
    assert "target price" not in encoded.lower()
