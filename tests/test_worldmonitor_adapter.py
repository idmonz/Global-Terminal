from __future__ import annotations

import requests

import lib.worldmonitor_adapter as wm


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"ok": True}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(str(self.status_code))

    def json(self):
        return self._payload


def test_worldmonitor_missing_base(monkeypatch):
    monkeypatch.delenv("WORLD_MONITOR_BASE_URL", raising=False)
    status = wm.check_worldmonitor_status()
    assert not status.ok


def test_worldmonitor_401_403_timeout(monkeypatch):
    monkeypatch.setenv("WORLD_MONITOR_BASE_URL", "https://example.test")

    monkeypatch.setattr(wm.requests, "get", lambda *args, **kwargs: FakeResponse(401))
    assert "key required" in wm.check_worldmonitor_status().error

    monkeypatch.setattr(wm.requests, "get", lambda *args, **kwargs: FakeResponse(403))
    forbidden = wm.check_worldmonitor_status()
    assert forbidden.is_paid_required

    def timeout(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(wm.requests, "get", timeout)
    assert "timed out" in wm.check_worldmonitor_status().error


def test_worldmonitor_route_intelligence_mock_path(monkeypatch):
    monkeypatch.setenv("WORLD_MONITOR_BASE_URL", "https://example.test")

    def fake_get(url, headers=None, params=None, timeout=12):
        assert url.endswith("/api/route-intelligence")
        assert params["fromIso2"] == "US"
        assert params["toIso2"] == "KR"
        return FakeResponse(200, {"route": "mock", "risk": "watch"})

    monkeypatch.setattr(wm.requests, "get", fake_get)
    status = wm.get_route_intelligence("US", "KR")
    assert status.ok
    assert status.data["route"] == "mock"
