from __future__ import annotations

from lib.data_contracts import UnifiedDataResult
from lib import financial_terminal
from lib import data_router


def test_financial_unified_payload_does_not_fabricate_estimates(monkeypatch):
    monkeypatch.setattr(data_router, "request_price_history", lambda *args, **kwargs: UnifiedDataResult(ok=True, provider="fake", source="fake", freshness="fresh", metadata={"source_confidence": 80}))
    monkeypatch.setattr(data_router, "request_financials", lambda *args, **kwargs: UnifiedDataResult(ok=True, provider="fake", source="fake", freshness="fresh", metadata={"source_confidence": 80}))

    payload = financial_terminal.build_unified_financial_endpoint_payload("AAPL")

    assert "does not fabricate" in payload["caveat"]
    assert "status_table" in payload
