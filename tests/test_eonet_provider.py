from __future__ import annotations

from lib.eonet_provider import build_eonet_events_url, normalize_eonet_geojson
from lib.event_stream import build_event_stream
from lib.live_feeds import fetch_nasa_eonet_events


def _feature(
    event_id: str,
    *,
    title: str,
    category_id: str,
    category_title: str,
    geometry: dict,
    date: str | None = None,
    geometry_dates: list[str] | None = None,
    source_url: str = "https://example.test/upstream",
) -> dict:
    properties = {
        "id": event_id,
        "title": title,
        "description": f"Source description for {title}",
        "link": f"https://eonet.gsfc.nasa.gov/api/v3/events/{event_id}/geojson",
        "categories": [{"id": category_id, "title": category_title}],
        "sources": [{"id": "UNIT", "url": source_url}],
    }
    if date:
        properties["date"] = date
    if geometry_dates:
        properties["geometryDates"] = geometry_dates
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def _payload() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            _feature(
                "EONET_FIRE",
                title="Earlier wildfire observation",
                category_id="wildfires",
                category_title="Wildfires",
                date="2026-07-25T10:00:00Z",
                geometry={"type": "Point", "coordinates": [-103.0, 44.5]},
            ),
            _feature(
                "EONET_FIRE",
                title="Current wildfire observation",
                category_id="wildfires",
                category_title="Wildfires",
                date="2026-07-27T11:21:00Z",
                geometry={"type": "Point", "coordinates": [-102.84, 44.76]},
            ),
            _feature(
                "EONET_STORM",
                title="Tracked severe storm",
                category_id="severeStorms",
                category_title="Severe Storms",
                geometry_dates=["2026-07-26 00:00:00", "2026-07-27 00:00:00"],
                geometry={
                    "type": "LineString",
                    "coordinates": [[130.0, 12.0], [132.0, 14.0]],
                },
            ),
            {"type": "Feature", "properties": {"id": "BROKEN"}, "geometry": None},
        ],
    }


def test_eonet_url_is_bounded_to_open_recent_geojson_events():
    url = build_eonet_events_url(days=30, status="open")

    assert url.startswith("https://eonet.gsfc.nasa.gov/api/v3/events/geojson?")
    assert "days=30" in url
    assert "status=open" in url


def test_eonet_normalization_deduplicates_and_uses_latest_track_coordinate():
    rows = normalize_eonet_geojson(
        _payload(),
        fetched_at="2026-07-30T00:00:00+00:00",
        limit=20,
    )
    by_id = {row["event_id"]: row for row in rows}

    assert len(rows) == 2
    assert by_id["EONET_FIRE"]["title"] == "Current wildfire observation"
    assert by_id["EONET_FIRE"]["lat"] == 44.76
    assert by_id["EONET_FIRE"]["layer_ids"] == ["fires"]
    assert by_id["EONET_FIRE"]["coordinate_method"] == "nasa_eonet_geojson_point"
    assert by_id["EONET_STORM"]["lat"] == 14.0
    assert by_id["EONET_STORM"]["lon"] == 132.0
    assert by_id["EONET_STORM"]["timestamp"].startswith("2026-07-27")
    assert by_id["EONET_STORM"]["layer_ids"] == ["storms_weather_alerts"]
    assert by_id["EONET_STORM"]["coordinate_method"] == "nasa_eonet_track_latest_point"
    assert by_id["EONET_STORM"]["data_gap"]
    assert by_id["EONET_STORM"]["eonet_url"].startswith("https://eonet.gsfc.nasa.gov/")
    assert by_id["EONET_STORM"]["source_url"].startswith("https://example.test/")
    assert all(row["provider"] == "nasa_eonet" for row in rows)
    assert all(row["not_financial_advice"] is True for row in rows)


def test_eonet_live_feed_adapter_preserves_provenance_and_bounds_rows():
    frame, status = fetch_nasa_eonet_events(
        requester=lambda _url: _payload(),
        days=30,
        limit=1,
    )

    assert status.ok
    assert len(frame) == 1
    assert status.provider == "nasa_eonet"
    assert {
        "provider",
        "source_url",
        "eonet_url",
        "fetched_at",
        "freshness",
        "source_status",
        "confidence",
        "coordinate_method",
        "data_gap",
        "caveat",
        "layer_ids",
    }.issubset(frame.columns)


def test_eonet_normalization_tolerates_malformed_unhashable_dates():
    feature = _feature(
        "EONET_MALFORMED_DATE",
        title="Natural event with malformed date",
        category_id="floods",
        category_title="Floods",
        geometry={"type": "Point", "coordinates": [127.0, 37.5]},
    )
    feature["properties"]["date"] = ["not", "a", "timestamp"]

    rows = normalize_eonet_geojson(
        {"type": "FeatureCollection", "features": [feature]},
        fetched_at="2026-07-30T00:00:00+00:00",
    )

    assert len(rows) == 1
    assert rows[0]["timestamp"] == "2026-07-30T00:00:00+00:00"
    assert rows[0]["coordinate_status"] == "source-backed"


def test_event_stream_does_not_collapse_nan_ids_from_mixed_provider_frames():
    rows = [
        {
            "event_id": float("nan"),
            "title": "USGS event one",
            "timestamp": "2026-07-30T00:00:00+00:00",
            "provider": "usgs_earthquake",
            "source": "USGS",
            "lat": 1.0,
            "lon": 2.0,
            "coordinate_method": "usgs_geojson",
        },
        {
            "event_id": float("nan"),
            "title": "USGS event two",
            "timestamp": "2026-07-30T00:01:00+00:00",
            "provider": "usgs_earthquake",
            "source": "USGS",
            "lat": 3.0,
            "lon": 4.0,
            "coordinate_method": "usgs_geojson",
        },
    ]

    events = build_event_stream(natural=rows, chokepoints=[])
    usgs_events = [row for row in events if row["provider"] == "usgs_earthquake"]

    assert len(usgs_events) == 2
    assert len({row["event_id"] for row in usgs_events}) == 2
