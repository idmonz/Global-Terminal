from __future__ import annotations

from lib.realtime_connectors import connect_aisstream_optional, connect_binance_websocket_optional, connect_opensky_optional, normalize_realtime_event, safe_close_connection


def test_realtime_connector_skeletons_are_optional(monkeypatch):
    monkeypatch.delenv("AISSTREAM_API_KEY", raising=False)
    monkeypatch.delenv("OPENSKY_CLIENT_ID", raising=False)
    monkeypatch.delenv("OPENSKY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OPENSKY_USERNAME", raising=False)
    monkeypatch.delenv("OPENSKY_PASSWORD", raising=False)

    assert connect_binance_websocket_optional()["status"] == "not_started"
    assert connect_aisstream_optional()["status"] == "unavailable"
    assert connect_opensky_optional()["status"] == "unavailable"
    event = normalize_realtime_event({"title": "Test", "provider": "mock"})
    assert event["severity"] == "watch"
    assert safe_close_connection(None)
