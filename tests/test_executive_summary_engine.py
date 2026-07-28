from __future__ import annotations

from lib.executive_summary_engine import build_global_executive_summary, build_user_friendly_briefing


def test_executive_summary_handles_missing_data_and_proxy_labels():
    summary = build_global_executive_summary(
        {
            "risk_score": 72,
            "data_gaps": ["NASA FIRMS key missing"],
            "proxy_outputs": ["chokepoint risk proxy"],
            "official_outputs": ["SEC EDGAR"],
            "provider_health": {"optional_missing": 1},
        }
    )
    assert summary["global_risk_state"] == "elevated"
    assert summary["missing_data"]
    assert "chokepoint risk proxy" in summary["proxy_outputs"]
    assert summary["provider_health"]["gap_count"] == 1


def test_user_friendly_briefing_schema():
    briefing = build_user_friendly_briefing({})
    assert briefing["title"]
    assert briefing["briefing"]
