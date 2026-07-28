from __future__ import annotations

from datetime import datetime, timezone

from lib.data_status import ok_result
from lib.layer_registry import build_layer_runtime_payload
from lib.opensky_provider import (
    OPENSKY_STATES_URL,
    build_opensky_optional_status,
    fetch_opensky_state_vectors,
)
from lib.provider_probe_runner import run_provider_probe
from lib.runtime_cache import clear_runtime_cache


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _OpenSkySession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, data=None, headers=None, timeout=None):
        self.posts.append({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return _Response({"access_token": "unit-token", "token_type": "Bearer", "expires_in": 1800})

    def get(self, url, params=None, headers=None, timeout=None):
        self.gets.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return _Response(
            {
                "time": 1710000000,
                "states": [
                    [
                        "abc123",
                        "KAL123 ",
                        "South Korea",
                        1710000000,
                        1710000005,
                        127.1,
                        37.5,
                        10000.0,
                        False,
                        250.0,
                        90.0,
                        0.0,
                        None,
                        10100.0,
                        "7000",
                        False,
                        0,
                        3,
                    ]
                ],
            }
        )


def test_opensky_state_vectors_use_oauth_and_normalize(monkeypatch):
    clear_runtime_cache()
    monkeypatch.setenv("OPENSKY_CLIENT_ID", "client")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "secret")
    session = _OpenSkySession()

    frame, status = fetch_opensky_state_vectors(time=1710000000, icao24="abc123", session=session, ttl_seconds=0)

    assert status.ok
    assert len(frame) == 1
    assert session.posts[0]["data"]["grant_type"] == "client_credentials"
    assert session.gets[0]["headers"]["Authorization"] == "Bearer unit-token"
    assert session.gets[0]["url"] == OPENSKY_STATES_URL
    assert frame.iloc[0]["callsign"] == "KAL123"
    assert frame.iloc[0]["lat"] == 37.5
    assert frame.iloc[0]["lon"] == 127.1
    assert frame.iloc[0]["velocity_kts"] > 480
    assert frame.iloc[0]["coordinate_method"] == "opensky_state_vector"
    assert frame.iloc[0]["position_source_label"] == "ads-b"
    assert frame.iloc[0]["provider"] == "opensky"
    assert frame.iloc[0]["source_url"] == OPENSKY_STATES_URL


def test_opensky_missing_credentials_stays_unavailable(monkeypatch):
    monkeypatch.delenv("OPENSKY_CLIENT_ID", raising=False)
    monkeypatch.delenv("OPENSKY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OPENSKY_USERNAME", raising=False)
    monkeypatch.delenv("OPENSKY_PASSWORD", raising=False)

    status_payload = build_opensky_optional_status()
    frame, status = fetch_opensky_state_vectors()

    assert status_payload["status"] == "unavailable"
    assert not status.ok
    assert frame.empty
    assert "OPENSKY_CLIENT_ID" in (status.error or "")


def test_opensky_layer_runtime_counts_authenticated_rows(monkeypatch):
    monkeypatch.setenv("OPENSKY_CLIENT_ID", "client")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "secret")
    fetched = datetime.now(timezone.utc).isoformat()
    runtime = {
        "flight": [
            {
                "provider": "opensky",
                "source": "OpenSky Network",
                "source_url": OPENSKY_STATES_URL,
                "fetched_at": fetched,
                "freshness": "fresh",
                "source_status": "fresh",
                "lat": 37.5,
                "lon": 127.1,
            }
        ]
    }
    payload = build_layer_runtime_payload(runtime, [ok_result(runtime["flight"], source="OpenSky /states/all", provider="opensky")])
    flight = next(layer for layer in payload["layers"] if layer["layer_id"] == "flight_tracking_unavailable")

    assert flight["row_count"] == 1
    assert flight["source_status"] == "live/fresh"
    assert flight["availability"] == "available"


def test_opensky_provider_probe_verifies_oauth_without_state_credit(monkeypatch):
    provider = {
        "provider_id": "opensky",
        "name": "OpenSky",
        "env_var": "OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET",
        "key_required": False,
        "no_key_fallback": True,
        "source_type": "official/public",
    }

    def _fake_token():
        return "token", ok_result({"expires_in": 1800}, source="token", provider="opensky_oauth")

    monkeypatch.setenv("OPENSKY_CLIENT_ID", "client")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "secret")
    monkeypatch.setattr("lib.opensky_provider.fetch_opensky_access_token", _fake_token)

    result = run_provider_probe(provider, dry_run=False)

    assert result["ok"] is True
    assert result["status"] == "oauth_verified"
    assert "/states/all credits" in result["caveat"]
