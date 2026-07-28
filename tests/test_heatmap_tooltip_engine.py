from __future__ import annotations

from lib.heatmap_tile_engine import prepare_heatmap_tiles
from lib.heatmap_tooltip_engine import build_crypto_tile_tooltip, build_heatmap_tooltip, build_provider_tile_tooltip


def test_heatmap_tooltips_include_truth_and_drilldown_fields():
    tile = prepare_heatmap_tiles([{"ticker": "BTC", "category": "Crypto", "funding_rate": 0.01, "source": "Binance", "freshness": "fresh"}], color_mode="funding_rate", group_mode="crypto_sector")[0]
    tooltip = build_heatmap_tooltip(tile)
    assert "Source: Binance" in tooltip
    assert "Freshness: fresh" in tooltip
    assert "Funding" in build_crypto_tile_tooltip(tile)
    assert "Configured" in build_provider_tile_tooltip(tile)
