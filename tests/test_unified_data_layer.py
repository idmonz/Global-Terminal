from __future__ import annotations

from lib.data_contracts import UnifiedDataResult
from lib import unified_data_layer


def test_unified_price_history_facade(monkeypatch):
    monkeypatch.setattr(unified_data_layer, "request_price_history", lambda symbol, **kwargs: UnifiedDataResult(ok=True, endpoint="price.history", provider="fake", metadata={"source_confidence": 90}))

    result = unified_data_layer.get_unified_price_history("SPY")

    assert result.ok
    assert result.endpoint == "price.history"


def test_unified_portfolio_inputs_reports_coverage(monkeypatch):
    monkeypatch.setattr(unified_data_layer, "get_unified_price_history", lambda symbol, **kwargs: UnifiedDataResult(ok=True, endpoint="price.history", provider="fake", metadata={"source_confidence": 80}))

    payload = unified_data_layer.get_unified_portfolio_inputs(["SPY", "TLT"])

    assert payload["coverage_pct"] == 100.0
    assert payload["source_confidence"] == 80.0
