from __future__ import annotations

from lib.heatmap_drilldown_engine import build_heatmap_command_suggestion, build_heatmap_drilldown_target, heatmap_crypto_to_crypto_intelligence_route


def test_heatmap_drilldown_engine_routes_assets_and_crypto():
    assert heatmap_crypto_to_crypto_intelligence_route("BTC")["command"] == "BTC CRYPTO"
    target = build_heatmap_drilldown_target({"label": "AAPL", "group": "Tech", "raw": {"ticker": "AAPL"}})
    assert target["page"] == "pages/15_Financial_Terminal.py"
    assert build_heatmap_command_suggestion({"label": "BTC", "raw": {"symbol": "BTC", "asset_class": "crypto"}}) == "BTC CRYPTO"
