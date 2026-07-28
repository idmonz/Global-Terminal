from __future__ import annotations

import pandas as pd

from lib import screeners
from lib.compliance import contains_forbidden_language


def test_unified_screener_backend_adds_factor_scores(monkeypatch):
    frame = pd.DataFrame({"ticker": ["AAPL"], "return_1m_pct": [5.0], "realized_volatility_pct": [20.0]})
    monkeypatch.setattr(screeners, "build_screener_with_source_mode", lambda asset_class, period="1y", source_mode="Auto": (frame, type("Status", (), {"refreshed_status": lambda self: "fresh"})(), {"openbb_installed": False, "fallback_allowed": True}))

    enriched, _, source_status = screeners.build_unified_screener_backend()

    assert "factor_coverage_score" in enriched.columns
    assert not contains_forbidden_language(str(enriched.to_dict()), allow_disclosure=False)
    assert source_status["factor_backend"] == "unified"
