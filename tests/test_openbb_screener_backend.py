from __future__ import annotations

import pandas as pd

from lib.data_status import ok_result
from lib.openbb_screener_backend import build_screener_source_status, build_screener_factor_presets, merge_native_and_openbb_screener_data


FORBIDDEN = ["Buy", "Sell", "Hold", "Strong Buy", "Strong Sell", "Trade now"]


def test_openbb_screener_merge_prefers_available_fields():
    native = pd.DataFrame([{"ticker": "AAA", "price": None, "sector": "Tech"}])
    openbb = pd.DataFrame([{"symbol": "AAA", "price": 12.5, "pe_ratio": 20}])

    merged = merge_native_and_openbb_screener_data(native, openbb)

    assert merged.iloc[0]["price"] == 12.5
    assert "data_quality_score" in merged.columns


def test_screener_source_status_present(monkeypatch):
    monkeypatch.setattr("lib.openbb_screener_backend.is_openbb_installed", lambda: False)
    status = build_screener_source_status("OpenBB preferred", ok_result(source="test", provider="openbb"))

    assert status["source_mode"] == "OpenBB preferred"
    assert status["fallback_allowed"] is True


def test_screener_presets_use_neutral_language():
    text = " ".join(str(item) for item in build_screener_factor_presets())

    assert "candidate" in text.lower()
    assert not any(term in text for term in FORBIDDEN)
