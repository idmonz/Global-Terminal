from __future__ import annotations

from lib.modern_visual_system import build_modern_card, build_visual_system_payload


def test_modern_visual_system_builds_summary_first_payload():
    payload = build_visual_system_payload("Overview", "Oil volatility and provider gaps are elevated.", context={"confidence": 72, "freshness": "fresh"})
    assert payload["header"]["title"] == "Overview"
    assert payload["summary"]["keywords"]
    assert payload["click_paths"]


def test_modern_card_includes_confidence_and_freshness():
    card = build_modern_card("Provider status", "Check freshness.", freshness="stale", confidence=45)
    assert card["freshness"]["status"] == "stale"
    assert card["confidence"]["value"] == 45
