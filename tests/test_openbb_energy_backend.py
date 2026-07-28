from __future__ import annotations

import pandas as pd

from lib.data_contracts import UnifiedDataResult
from lib import openbb_energy_backend


def test_energy_backend_labels_proxy_data(monkeypatch):
    monkeypatch.setattr(openbb_energy_backend, "request_energy_data", lambda endpoint, **kwargs: UnifiedDataResult(ok=True, data=pd.DataFrame({"ticker": ["CL=F"], "latest_price": [80]}), provider="yfinance", source="proxy", endpoint=endpoint, freshness="estimated", is_proxy=True, metadata={"source_confidence": 50}))

    payload = openbb_energy_backend.build_energy_dashboard_payload()

    assert payload["status_table"]["proxy"].any()
    assert payload["source_confidence"] == 50
