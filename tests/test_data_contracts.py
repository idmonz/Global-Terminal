from __future__ import annotations

from lib.data_contracts import DataRequest, UnifiedDataResult


def test_data_request_normalizes_source_mode_and_symbol():
    request = DataRequest(endpoint="price.history", symbol="spy", source_mode="OpenBB preferred")

    assert request.source_mode == "openbb_preferred"
    assert request.symbol == "SPY"
    assert request.symbols == ["SPY"]


def test_unified_data_result_serializes_gaps():
    result = UnifiedDataResult(ok=True, endpoint="price.history", provider="native")

    assert result.to_dict()["ok"] is True
    assert result.to_dict()["endpoint"] == "price.history"
