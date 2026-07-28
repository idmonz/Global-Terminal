from __future__ import annotations

from lib.data_contracts import DataRequest
from lib.provider_router import fallback_provider_chain, provider_missing_key_gaps, resolve_provider_route


def test_provider_router_uses_native_when_openbb_missing(monkeypatch):
    monkeypatch.setattr("lib.provider_router.is_openbb_installed", lambda: False)

    route = resolve_provider_route(DataRequest(endpoint="price.history", symbol="SPY", source_mode="auto"))

    assert route.provider != "openbb"
    assert route.native is True


def test_provider_router_respects_openbb_only(monkeypatch):
    monkeypatch.setattr("lib.provider_router.is_openbb_installed", lambda: False)

    route = resolve_provider_route(DataRequest(endpoint="equity.financials.income", symbol="AAPL", source_mode="openbb_only"))

    assert route.provider == "openbb"
    assert route.openbb is True


def test_provider_key_gaps_do_not_show_secret(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.setenv("INTRINIO_API_KEY", "supersecret")

    gaps = provider_missing_key_gaps("equity.financials.income", "openbb")

    assert gaps
    assert "supersecret" not in str([gap.to_dict() for gap in gaps]).lower()
    assert "openbb" in fallback_provider_chain(DataRequest(endpoint="equity.financials.income", symbol="AAPL", source_mode="openbb_preferred"))
