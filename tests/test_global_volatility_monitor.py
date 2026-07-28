from __future__ import annotations

from lib.global_volatility_monitor import build_global_volatility_monitor, classify_global_volatility_state, compute_drawdown_state, compute_volatility_zscore


def test_global_volatility_monitor_flags_elevated_risk():
    rows = [{"ticker": "VIX", "asset_class": "Vol", "realized_vol": 45, "drawdown_52w": -2, "vol_history": [10, 15, 20]}]
    payload = build_global_volatility_monitor(rows)
    assert payload["ranking"][0]["risk_score"] > 50
    assert payload["heatmap"]["tiles"]
    assert compute_volatility_zscore(30, [10, 20]) > 0
    assert compute_drawdown_state(-25) == "severe drawdown"
    assert classify_global_volatility_state(2.1) == "severe"
