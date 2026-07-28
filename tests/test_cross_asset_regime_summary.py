from __future__ import annotations

from lib.cross_asset_regime_summary import build_cross_asset_regime_matrix, summarize_cross_asset_regime


def test_cross_asset_regime_matrix_has_components():
    summary = summarize_cross_asset_regime({"equity": {"score": 80}, "crypto": {"score": 70}})
    matrix = build_cross_asset_regime_matrix({})
    assert summary["state"] in {"watch", "elevated", "stressed", "calm"}
    assert len(matrix) == 6
