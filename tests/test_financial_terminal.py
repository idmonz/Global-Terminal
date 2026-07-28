from __future__ import annotations

import pandas as pd

from lib.data_status import ok_result
from lib import financial_terminal as ft


def test_financial_terminal_missing_data_payload(monkeypatch):
    def fake_overview(ticker, period="annual"):
        return {
            "ticker": ticker,
            "period": period,
            "income": pd.DataFrame(),
            "balance": pd.DataFrame(),
            "cashflow": pd.DataFrame(),
            "growth": pd.DataFrame(),
            "margins": pd.DataFrame(),
            "ratios": {},
            "availability": {"income": False, "balance": False, "cashflow": False, "ratios": False},
            "data_gaps": ["income", "balance", "cashflow", "ratios"],
        }, ok_result({}, source="fake", provider="test", coverage="missing")

    monkeypatch.setattr(ft, "build_fundamental_overview", fake_overview)
    payload, status, caveats = ft.build_financial_overview("ZZZ", period="quarterly")
    assert payload["period"] == "quarterly"
    assert payload["data_gaps"]
    assert caveats


def test_financial_terminal_period_fallback_for_older_fundamentals(monkeypatch):
    def legacy_overview(ticker):
        return {
            "ticker": ticker,
            "income": pd.DataFrame(),
            "balance": pd.DataFrame(),
            "cashflow": pd.DataFrame(),
            "growth": pd.DataFrame(),
            "margins": pd.DataFrame(),
            "ratios": {},
            "availability": {},
            "data_gaps": [],
        }, ok_result({}, source="legacy fake", provider="test")

    monkeypatch.setattr(ft, "build_fundamental_overview", legacy_overview)
    payload, status, caveats = ft.build_financial_overview("ZZZ", period="quarterly")
    assert payload["period"] == "annual"
    assert "period_request_data_gap" in payload
    assert "annual fallback" in status.warning
    assert caveats


def test_data_availability_matrix_with_monkeypatch(monkeypatch):
    empty = pd.DataFrame()
    monkeypatch.setattr(ft, "get_financial_statements", lambda ticker, period="annual": ({"income": empty, "balance": empty, "cashflow": empty, "period": period}, ok_result({}, source="fake statements", provider="test")))
    monkeypatch.setattr(ft, "get_key_ratios", lambda ticker: ({}, ok_result({}, source="fake ratios", provider="test")))
    monkeypatch.setattr(ft, "build_earnings_panel", lambda ticker: ({"has_estimates": False}, ok_result({}, source="fake earnings", provider="test"), ["gap"]))
    matrix, status, caveats = ft.build_data_availability_matrix("ZZZ")
    assert not matrix.empty
    assert matrix["available"].eq(False).any()
    assert status.ok
    assert caveats
