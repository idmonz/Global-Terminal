from __future__ import annotations

import pandas as pd

from lib.data_contracts import UnifiedDataResult
from lib import openbb_macro_backend


def test_macro_backend_builds_dashboard_with_gaps(monkeypatch):
    def fake_series(series_id, **kwargs):
        return UnifiedDataResult(ok=True, data=pd.DataFrame({"date": ["2024-01-01"], "value": [1]}), provider="fake", source="fake", endpoint="macro.fred_series", freshness="fresh", metadata={"source_confidence": 80})

    monkeypatch.setattr(openbb_macro_backend, "request_macro_series", fake_series)
    monkeypatch.setattr(openbb_macro_backend, "request_rates_curve", lambda **kwargs: UnifiedDataResult(ok=True, data=pd.DataFrame({"maturity": ["10Y"], "rate": [4.0]}), provider="fake", source="fake", endpoint="rates.treasury_curve", freshness="fresh", metadata={"source_confidence": 80}))

    payload = openbb_macro_backend.build_macro_rates_dashboard_payload()

    assert payload["source_confidence"] == 80
    assert "treasury_curve" in payload["results"]
