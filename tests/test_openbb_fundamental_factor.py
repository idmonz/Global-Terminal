from __future__ import annotations

import pandas as pd

from lib.data_contracts import UnifiedDataResult
from lib import openbb_fundamental_factor


def test_fundamental_factor_scores_do_not_fabricate_missing_fields(monkeypatch):
    def fake_financials(symbol, statement="ratios", **kwargs):
        data = pd.DataFrame({"symbol": [symbol], "pe": [10], "roe": [0.2], "debt_to_equity": [0.5]}) if statement in {"ratios", "metrics"} else pd.DataFrame({"date": ["2024-01-01"], "revenue": [100], "net_income": [20]})
        return UnifiedDataResult(ok=True, data=data, provider="fake", source="fake", endpoint=statement, freshness="fresh", metadata={"source_confidence": 80})

    monkeypatch.setattr(openbb_fundamental_factor, "request_financials", fake_financials)

    scores = openbb_fundamental_factor.build_fundamental_factor_scores("AAPL")

    assert scores["value_score"] > 0
    assert "not fabricated" in scores["caveat"]
