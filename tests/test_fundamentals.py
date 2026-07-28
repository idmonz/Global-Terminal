from __future__ import annotations

import pandas as pd

from lib.fundamentals import compute_balance_sheet_quality, compute_growth_rates, compute_margin_series, normalize_financial_statement


def test_statement_normalization_and_growth():
    raw = pd.DataFrame(
        {
            "2024-12-31": [100, 20],
            "2025-12-31": [125, 30],
        },
        index=["Total Revenue", "Net Income"],
    )
    normalized = normalize_financial_statement(raw, {"revenue": ["Total Revenue"], "net_income": ["Net Income"]})
    assert list(normalized.columns) == ["revenue", "net_income"]
    growth = compute_growth_rates(normalized, ["revenue", "net_income"])
    assert round(growth["revenue"].dropna().iloc[-1], 2) == 25.0


def test_margin_calculation_and_missing_path():
    income = pd.DataFrame({"revenue": [100.0], "gross_profit": [50.0], "operating_income": [25.0], "net_income": [10.0]})
    margins = compute_margin_series(income)
    assert margins["gross_margin"].iloc[0] == 50.0
    missing = compute_margin_series(pd.DataFrame())
    assert missing.empty


def test_balance_sheet_quality():
    balance = pd.DataFrame({"cash_and_equivalents": [10.0], "total_debt": [25.0], "total_assets": [100.0], "shareholders_equity": [40.0]})
    quality = compute_balance_sheet_quality(balance)
    assert quality["net_debt"] == 15.0
    assert quality["debt_to_assets"] == 0.25
