from __future__ import annotations

import pandas as pd

from lib.openbb_data_mapper import map_openbb_estimates, map_openbb_price_history, map_openbb_equity_profile


def test_price_history_mapper_normalizes_aliases():
    frame = map_openbb_price_history([{"datetime": "2024-01-01", "Open": 10, "Close": 11, "Volume": 100}])

    assert list(frame.columns) == ["date", "open", "close", "volume"]
    assert pd.notna(frame.iloc[0]["date"])


def test_mapper_returns_empty_warning_for_insufficient_data():
    frame = map_openbb_price_history([{"date": "2024-01-01", "volume": 100}])

    assert frame.empty
    assert "lacks close" in frame.attrs["warning"]


def test_estimates_are_labeled_as_estimates():
    frame = map_openbb_estimates([{"date": "2024-01-01", "estimated_eps": 2.5}])

    assert frame.attrs["is_estimate"] is True
    assert bool(frame["is_estimate"].iloc[0])


def test_profile_mapper_keeps_missing_fields_missing():
    frame = map_openbb_equity_profile([{"symbol": "AAPL", "name": "Apple"}])

    assert frame.iloc[0]["ticker"] == "AAPL"
    assert "market_cap" not in frame.columns or pd.isna(frame.iloc[0].get("market_cap"))
