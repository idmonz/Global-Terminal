from __future__ import annotations

from lib.heatmap_tile_engine import build_treemap_dataframe, compute_tile_size, prepare_heatmap_tiles


def test_heatmap_tile_engine_market_cap_fallback_and_metadata():
    rows = [{"ticker": "AAPL", "sector": "Tech", "daily_return": 2.0}, {"ticker": "XOM", "sector": "Energy", "market_cap": 10, "daily_return": -1.0}]
    tiles = prepare_heatmap_tiles(rows, size_mode="market_cap", color_mode="daily_change", group_mode="sector")
    assert tiles[0]["size_mode"] == "equal_fallback"
    assert "missing market_cap" in tiles[0]["metadata"]["data_gaps"]
    assert compute_tile_size(rows[1], "market_cap")["size"] == 10
    assert len(build_treemap_dataframe(tiles)) == 2
