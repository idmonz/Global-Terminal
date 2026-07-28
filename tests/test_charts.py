from __future__ import annotations

import pandas as pd

from lib.charts import normalize_price_history_columns


def test_normalize_price_history_columns_field_then_ticker():
    dates = pd.date_range("2026-01-01", periods=3)
    frame = pd.DataFrame(
        [[100, 101, 99], [101, 102, 100], [102, 103, 101]],
        index=dates,
        columns=pd.MultiIndex.from_tuples([("Adj Close", "AAPL"), ("Close", "AAPL"), ("Low", "AAPL")]),
    )

    output = normalize_price_history_columns(frame, "AAPL")

    assert list(output.columns) == ["Adj Close", "Close", "Low"]
    assert output["Adj Close"].iloc[-1] == 102


def test_normalize_price_history_columns_ticker_then_field():
    dates = pd.date_range("2026-01-01", periods=3)
    frame = pd.DataFrame(
        [[100, 101, 1000], [101, 102, 1001], [102, 103, 1002]],
        index=dates,
        columns=pd.MultiIndex.from_tuples([("MSFT", "Open"), ("MSFT", "Close"), ("MSFT", "Volume")]),
    )

    output = normalize_price_history_columns(frame, "MSFT")

    assert list(output.columns) == ["Open", "Close", "Volume"]
    assert output["Close"].iloc[0] == 101
