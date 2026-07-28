from __future__ import annotations

import pandas as pd

from lib.alpha_library import compute_momentum_signal, compute_multi_signal_score, compute_trend_signal, generate_alpha_combinations


def test_alpha_signals_have_neutral_schema():
    prices = pd.DataFrame({"AAA": range(100, 180), "BBB": range(80, 160)}, index=pd.date_range("2024-01-01", periods=80))
    signals = compute_momentum_signal(prices) + compute_trend_signal(prices)
    score = compute_multi_signal_score(signals)

    assert signals
    assert {"signal_name", "family", "asset", "score", "direction_label", "evidence", "data_gaps", "caveat"}.issubset(signals[0])
    assert set(score["direction_label"]).issubset({"constructive", "neutral", "deteriorating", "defensive", "crowded", "data_gap"})


def test_generate_alpha_combinations_is_available_from_alpha_library():
    combos = generate_alpha_combinations(["momentum", "quality"], max_size=2)

    assert [combo["families"] for combo in combos] == [["momentum"], ["quality"], ["momentum", "quality"]]
    assert all("research candidate" in combo["caveat"] for combo in combos)
