from __future__ import annotations

from lib.data_status import error_result, ok_result


def test_data_result_statuses():
    ok = ok_result({"x": 1}, source="unit", provider="test")
    missing = error_result(source="unit", provider="test", error="missing")

    assert ok.ok
    assert ok.refreshed_status() == "fresh"
    assert not missing.ok
    assert missing.refreshed_status() in {"missing", "error"}
    assert "fetched_at" in ok.to_dict()

