from __future__ import annotations

import pandas as pd

from lib.schema_normalizer import normalize_price_history, normalize_screener_rows


def test_schema_normalizer_handles_missing_columns_without_crash():
    frame, gaps = normalize_price_history(pd.DataFrame({"Date": ["2024-01-01"], "Close": [100]}), symbol="SPY")

    assert "close" in frame.columns
    assert frame.iloc[0]["symbol"] == "SPY"
    assert any(gap.field == "open" for gap in gaps)


def test_screener_normalizer_adds_ticker_from_symbol():
    frame, _ = normalize_screener_rows([{"symbol": "AAPL", "price": 100}])

    assert frame.iloc[0]["ticker"] == "AAPL"
