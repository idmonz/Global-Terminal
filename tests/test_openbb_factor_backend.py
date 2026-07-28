from __future__ import annotations

from lib.data_contracts import UnifiedDataResult
from lib import openbb_factor_backend


def test_factor_backend_table_reports_coverage(monkeypatch):
    monkeypatch.setattr(openbb_factor_backend, "get_technical_factor_bundle", lambda symbol, source_mode="auto": {"rsi": UnifiedDataResult(ok=True, metadata={"source_confidence": 80})})
    monkeypatch.setattr(openbb_factor_backend, "build_fundamental_factor_scores", lambda symbol, source_mode="auto": {"value_score": 50, "quality_score": 60, "growth_score": 70, "profitability_score": 80, "data_quality_score": 90, "data_gaps": []})
    monkeypatch.setattr(openbb_factor_backend, "build_options_factor_scores", lambda symbol, source_mode="auto": {"options_activity_score": 55, "source_confidence": 60, "data_gaps": []})
    monkeypatch.setattr(openbb_factor_backend, "build_rates_macro_factor_scores", lambda source_mode="auto": {"score": 65, "source_confidence": 70, "data_gaps": []})

    payload = openbb_factor_backend.build_factor_backend_table(["SPY"])

    assert payload["table"].iloc[0]["factor_coverage_pct"] > 0
