from __future__ import annotations

import pandas as pd

from lib.data_status import error_result, ok_result
from lib import financial_terminal


def _native_state():
    status = ok_result(pd.DataFrame([{"x": 1}]), source="native", provider="yfinance")
    return {
        "ticker": "AAPL",
        "period": "annual",
        "header": {},
        "overview": {"data_gaps": []},
        "statuses": [status],
        "status": status,
        "caveats": [],
        "availability": pd.DataFrame(),
    }


def test_financial_terminal_openbb_preferred_falls_back_to_native(monkeypatch):
    monkeypatch.setattr(financial_terminal, "is_openbb_installed", lambda: False)
    monkeypatch.setattr(financial_terminal, "_build_native_financial_terminal_state", lambda ticker, period="annual": _native_state())

    state = financial_terminal.build_financial_terminal_state("AAPL", source_mode="OpenBB preferred")

    assert state["source_provider"] == "native"
    assert state["fallback_used"] is True
    assert state["openbb_installed"] is False


def test_financial_terminal_openbb_only_does_not_use_native(monkeypatch):
    called = {"native": False}
    monkeypatch.setattr(financial_terminal, "is_openbb_installed", lambda: False)

    def native(*args, **kwargs):
        called["native"] = True
        return _native_state()

    monkeypatch.setattr(financial_terminal, "_build_native_financial_terminal_state", native)
    missing = error_result(source="openbb", provider="openbb", error="OpenBB unavailable", data=pd.DataFrame())
    for name in [
        "get_openbb_company_profile",
        "get_openbb_price_history",
        "get_openbb_income_statement",
        "get_openbb_balance_sheet",
        "get_openbb_cash_flow",
        "get_openbb_ratios",
        "get_openbb_metrics",
        "get_openbb_estimates",
        "get_openbb_revenue_segments",
        "get_openbb_revenue_geography",
        "get_openbb_filings",
        "get_openbb_peers",
        "get_openbb_ownership",
    ]:
        monkeypatch.setattr(financial_terminal, name, lambda *args, **kwargs: missing)

    state = financial_terminal.build_financial_terminal_state("AAPL", source_mode="OpenBB only")

    assert called["native"] is False
    assert state["source_provider"] == "openbb"
    assert state["status"].ok is False
