from __future__ import annotations

import pandas as pd

from lib.signal_fusion import (
    build_signal_convergence_table,
    fuse_crypto_signals,
    fuse_energy_signals,
    fuse_market_signals,
    fuse_news_signals,
    normalize_signal,
)


def test_signal_normalization_and_fusion_schema():
    signal = normalize_signal("VIX", 65, category="risk", confidence=0.7, source_status="fresh")
    assert signal["score"] == 65
    assert signal["label"] == "Elevated volatility"
    market = fuse_market_signals(cards=pd.DataFrame([{"label": "S&P 500", "change_pct": 1.2, "period_return_pct": 4.0, "data_status": "fresh"}]))
    crypto = fuse_crypto_signals({"funding_rate": 0.0004, "global_long_short_ratio": 1.2})
    energy = fuse_energy_signals({"inventory_status": "EIA optional key unavailable", "chokepoint_risk_proxy": "Static chokepoint registry"})
    news = fuse_news_signals({"impact_matrix": pd.DataFrame([{"critical_count": 0, "high_count": 2, "medium_count": 1, "total_count": 3}])})
    table = build_signal_convergence_table([market, crypto, energy, news])

    assert {"category", "average_score", "dominant_label", "method"}.issubset(table.columns)
    assert table["average_score"].between(0, 100).all()
