from __future__ import annotations

import pandas as pd

from lib.portfolio_quant_lab import RESEARCH_DISCLOSURE, build_quant_lab_snapshot, methodology_notes


def test_quant_lab_snapshot_schema():
    rows = [
        {"ticker": "AAA", "asset_class": "stock", "weight": 0.6, "include": True},
        {"ticker": "BBB", "asset_class": "ETF", "weight": 0.4, "include": True},
    ]
    prices = pd.DataFrame({"AAA": range(100, 180), "BBB": range(80, 160)}, index=pd.date_range("2024-01-01", periods=80))
    snapshot = build_quant_lab_snapshot(rows, prices)

    assert snapshot["status"].ok
    assert "backtest" in snapshot
    assert "strategy_candidates" in snapshot
    assert "forecast" in snapshot
    assert RESEARCH_DISCLOSURE in [note["note"] for note in methodology_notes()]
