from __future__ import annotations

import pandas as pd

from lib import portfolio_factor_router


def test_portfolio_factor_router_returns_factor_coverage(monkeypatch):
    def fake_table(symbols, source_mode="auto"):
        table = pd.DataFrame({"symbol": symbols, "factor_coverage_pct": [80] * len(symbols), "source_confidence": [70] * len(symbols), "value_score": [50] * len(symbols), "quality_score": [60] * len(symbols), "growth_score": [55] * len(symbols), "profitability_score": [65] * len(symbols), "options_activity_score": [20] * len(symbols), "rates_macro_score": [45] * len(symbols), "data_gap_count": [0] * len(symbols)})
        return {"table": table, "payloads": {symbol: {"data_gaps": []} for symbol in symbols}}

    monkeypatch.setattr(portfolio_factor_router, "build_factor_backend_table", fake_table)
    rows = [{"ticker": "SPY", "weight": 1.0, "include": True}]

    profile = portfolio_factor_router.build_portfolio_factor_profile(rows)
    matrix = portfolio_factor_router.build_strategy_factor_matrix(rows)

    assert profile["factor_coverage_pct"] == 80
    assert "source_confidence" in matrix.columns
