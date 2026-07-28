from __future__ import annotations

from lib.live_feeds import (
    AIS_UNAVAILABLE_MESSAGE,
    FLIGHT_UNAVAILABLE_MESSAGE,
    build_live_feed_status,
    fetch_aisstream_optional_status,
    fetch_gdelt_feed,
    fetch_opensky_optional_status,
    fetch_usgs_earthquakes,
)


def test_live_feed_optional_status_and_mock_fetches(monkeypatch):
    monkeypatch.delenv("AISSTREAM_API_KEY", raising=False)
    monkeypatch.delenv("OPENSKY_CLIENT_ID", raising=False)
    monkeypatch.delenv("OPENSKY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OPENSKY_USERNAME", raising=False)
    monkeypatch.delenv("OPENSKY_PASSWORD", raising=False)

    assert fetch_aisstream_optional_status()["warning"] == AIS_UNAVAILABLE_MESSAGE
    assert fetch_opensky_optional_status()["warning"] == FLIGHT_UNAVAILABLE_MESSAGE
    assert not build_live_feed_status().empty

    gdelt, gdelt_status = fetch_gdelt_feed(requester=lambda query: [{"title": query, "source": "mock"}])
    assert gdelt_status.ok and len(gdelt) == 1
    assert {"provider", "source_url", "fetched_at", "freshness", "source_status", "confidence", "coordinate_method", "data_gap", "caveat"}.issubset(gdelt.columns)
    usgs, usgs_status = fetch_usgs_earthquakes(requester=lambda url: {"features": [{"properties": {"title": "M 5.0"}, "geometry": {"coordinates": [1, 2]}}]})
    assert usgs_status.ok and usgs.iloc[0]["lat"] == 2
    assert usgs.iloc[0]["provider"] == "usgs_earthquake"
    assert usgs.iloc[0]["coordinate_method"] == "usgs_geojson"
