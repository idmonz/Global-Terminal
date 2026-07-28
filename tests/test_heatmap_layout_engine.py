from __future__ import annotations

from lib.heatmap_layout_engine import build_energy_risk_heatmap, build_heatmap_layout, build_provider_health_heatmap


def test_heatmap_layout_engine_builds_payloads():
    payload = build_heatmap_layout([{"ticker": "AAPL", "sector": "Tech", "market_cap": 10, "daily_return": 1}], title="Unit")
    assert payload["title"] == "Unit"
    assert payload["tiles"][0]["command_suggestion"] == "AAPL FA"
    assert build_provider_health_heatmap([{"provider_id": "gdelt", "domain": "news", "score": 80}])["tiles"]
    assert build_energy_risk_heatmap([{"name": "Hormuz", "risk_score": 80}])["tiles"]
