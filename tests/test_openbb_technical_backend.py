from __future__ import annotations

import pandas as pd

from lib.data_contracts import UnifiedDataResult
from lib import openbb_technical_backend


def test_technical_backend_calculates_rsi_from_native_history(monkeypatch):
    frame = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=40), "close": range(40), "high": range(40), "low": range(40)})
    monkeypatch.setattr(openbb_technical_backend, "_history", lambda symbol, source_mode="auto", **kwargs: UnifiedDataResult(ok=True, data=frame, provider="fake", source="fake", endpoint="price.history", freshness="fresh", metadata={"source_confidence": 80}))

    result = openbb_technical_backend.get_rsi_unified("SPY")

    assert result.endpoint == "technical.rsi"
    assert "rsi" in result.data.columns
