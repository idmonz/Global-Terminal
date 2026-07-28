from __future__ import annotations

import pandas as pd

from lib.data_contracts import UnifiedDataResult
from lib import openbb_shipping_backend


def test_shipping_backend_does_not_claim_live_ais(monkeypatch):
    monkeypatch.setattr(openbb_shipping_backend, "request_shipping_data", lambda endpoint, **kwargs: UnifiedDataResult(ok=True, data=pd.DataFrame({"chokepoint": ["Suez"]}), provider="static", source="static", endpoint=endpoint, freshness="estimated", is_proxy=True, metadata={"source_confidence": 40}))

    payload = openbb_shipping_backend.build_shipping_chokepoint_payload()

    assert "No live AIS" in payload["status_table"].iloc[0]["caveat"]
    assert payload["status_table"]["proxy"].all()
