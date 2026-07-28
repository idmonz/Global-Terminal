from __future__ import annotations

from lib.nws_provider import build_nws_points_url, fetch_nws_points


def test_nws_requires_user_agent(monkeypatch):
    monkeypatch.delenv("NWS_USER_AGENT", raising=False)
    result = fetch_nws_points(38.0, -77.0)
    assert result["status"] == "missing_key"
    assert build_nws_points_url(38.0, -77.0).endswith("/points/38.0,-77.0")
