from __future__ import annotations

from lib import openbb_rates_factor


def test_rates_factor_scores_handle_data_gaps(monkeypatch):
    monkeypatch.setattr(openbb_rates_factor, "build_macro_rates_dashboard_payload", lambda source_mode="auto": {"status_table": [], "data_gaps": ["gap"], "source_confidence": 40})

    scores = openbb_rates_factor.build_rates_macro_factor_scores()

    assert scores["score"] >= 0
    assert scores["data_gaps"] == ["gap"]
