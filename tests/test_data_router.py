from __future__ import annotations

import pandas as pd

from lib.data_contracts import UnifiedDataResult
from lib.data_status import ok_result
from lib.data_router import request_data, request_financials, request_price_history


def test_data_router_native_price_history_fallback(monkeypatch):
    def fake_history(symbol, period="1y", interval="1d"):
        frame = pd.DataFrame({"date": ["2024-01-01"], "close": [100.0]})
        return frame, ok_result(frame, source=symbol, provider="fake")

    monkeypatch.setattr("lib.market_data.fetch_price_history", fake_history)

    result = request_price_history("SPY", source_mode="native_only")

    assert result.ok
    assert result.native_used is True
    assert result.data.iloc[0]["close"] == 100.0


def test_data_router_openbb_missing_openbb_only_returns_warning(monkeypatch):
    monkeypatch.setattr("lib.provider_router.is_openbb_installed", lambda: False)
    monkeypatch.setattr("lib.openbb_bridge.importlib.import_module", lambda name: (_ for _ in ()).throw(ImportError("missing")))

    result = request_data({"endpoint": "equity.financials.income", "symbol": "AAPL", "source_mode": "openbb_only"})

    assert not result.ok
    assert result.openbb_used or result.provider in {"openbb", "data_gap"}
    assert result.errors or result.warnings


def test_data_router_allows_endpoint_flag_overrides(monkeypatch):
    captured = {}

    def fake_native(request):
        captured["allow_proxy"] = request.allow_proxy
        captured["allow_estimates"] = request.allow_estimates
        frame = pd.DataFrame({"symbol": ["AAPL"], "pe": [25.0]})
        return UnifiedDataResult(
            ok=True,
            data=frame,
            provider="fake",
            source="fake",
            endpoint=request.endpoint,
            native_used=True,
        )

    monkeypatch.setattr("lib.data_router._call_native", fake_native)

    result = request_financials(
        "AAPL",
        statement="ratios",
        source_mode="native_only",
        allow_proxy=True,
        allow_estimates=True,
    )

    assert result.ok
    assert result.endpoint == "equity.financials.ratios"
    assert captured == {"allow_proxy": True, "allow_estimates": True}
