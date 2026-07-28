from __future__ import annotations

from pathlib import Path

import lib.war_room as war_room
from lib.event_stream import build_event_stream
from lib.map_news_event_fusion import build_map_news_event_fusion_contract
from lib.war_room_map import build_war_room_map_contract


ROOT = Path(__file__).resolve().parents[1]


def _layer_payload() -> dict:
    return {
        "layers": [
            {
                "layer_id": "earthquakes",
                "label": "Earthquakes",
                "domain": "natural",
                "provider": "usgs_earthquake",
                "source_status": "live/fresh",
                "availability": "available",
                "row_count": 2,
                "requires_key": None,
            },
            {
                "layer_id": "flight_tracking_unavailable",
                "label": "OpenSky Flight Tracking",
                "domain": "flight",
                "provider": "opensky",
                "source_status": "unavailable",
                "availability": "unavailable",
                "row_count": 0,
                "requires_key": "OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET",
            },
        ]
    }


def _event(event_id: str, method: str, domain: str = "natural") -> dict:
    return {
        "event_id": event_id,
        "title": f"{event_id} source event",
        "summary": "Official source row.",
        "timestamp": "2026-06-20T00:00:00+00:00",
        "lat": 37.4,
        "lon": 141.7,
        "coordinate_method": method,
        "provider": "usgs_earthquake" if domain == "natural" else "opensky",
        "source": "official provider",
        "source_url": "https://example.test/event",
        "fetched_at": "2026-06-20T00:01:00+00:00",
        "freshness": "live/fresh",
        "source_status": "live/fresh",
        "confidence": 0.95,
        "severity": "high",
        "region": "Global",
        "domain": domain,
        "data_gap": "",
        "caveat": "Provider rows can revise.",
    }


def test_provider_native_coordinates_are_source_backed_and_freshness_is_explicit():
    contract = build_war_room_map_contract(
        events=[_event("usgs-1", "usgs_geojson"), _event("flight-1", "opensky_state_vector", "flight")],
        layer_runtime=_layer_payload(),
        provider_rows=[],
        event_graph={"nodes": [], "edges": []},
    )

    markers = {row["event_id"]: row for row in contract["markers"]}
    assert markers["usgs-1"]["coordinate_status"] == "source-backed"
    assert markers["flight-1"]["coordinate_status"] == "source-backed"
    assert all(row["freshness"] == "live/fresh" for row in markers.values())
    assert all(row["source_url"].startswith("https://") for row in markers.values())


def test_layer_visible_marker_counts_match_returned_marker_membership():
    contract = build_war_room_map_contract(
        events=[_event("usgs-1", "usgs_geojson"), _event("usgs-2", "usgs_geojson")],
        layer_runtime=_layer_payload(),
        provider_rows=[],
        event_graph={"nodes": [], "edges": []},
    )

    layers = {row["layer_id"]: row for row in contract["layers"]}
    assert layers["earthquakes"]["visible_marker_count"] == 2
    assert layers["flight_tracking_unavailable"]["visible_marker_count"] == 0
    assert contract["summary"]["visible_marker_count"] == len(contract["markers"])


def test_flight_rows_join_event_stream_without_losing_provider_provenance():
    rows = build_event_stream(
        flight=[_event("flight-1", "opensky_state_vector", "flight")],
        chokepoints=[],
    )

    flight = next(row for row in rows if row["domain"] == "flight")
    assert flight["provider"] == "opensky"
    assert flight["coordinate_method"] == "opensky_state_vector"
    assert flight["source_status"] == "live/fresh"


def test_env_configured_optional_flights_are_attempted_but_failure_creates_no_fake_rows(monkeypatch):
    captured: dict = {}

    def fake_runtime(**kwargs):
        captured.update(kwargs)
        return {
            "news": [],
            "natural": [],
            "crypto": [],
            "flight": [],
            "source_statuses": [],
            "source_status": [{"provider": "opensky", "ok": False, "error": "401 rejected"}],
            "data_gaps": ["opensky: 401 rejected"],
        }

    monkeypatch.setenv("OPENSKY_CLIENT_ID", "configured-client")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "configured-secret")
    monkeypatch.setattr(war_room, "build_keyless_runtime_feeds", fake_runtime)

    state = war_room.build_war_room_state(include_default_runtime=True)

    assert captured["include_flights"] is True
    assert not any(row.get("domain") == "flight" for row in state["events"])
    assert any("401 rejected" in gap for gap in state["runtime_feeds"]["data_gaps"])


def test_fusion_exposes_full_news_register_for_client_selected_event_matching():
    marker = build_war_room_map_contract(
        events=[_event("usgs-1", "usgs_geojson")],
        layer_runtime=_layer_payload(),
        provider_rows=[],
        event_graph={"nodes": [], "edges": []},
    )
    news = [
        {"title": "Japan earthquake update", "region": "Global", "provider": "rss", "source_status": "live/fresh", "source_url": "https://example.test/news-1"},
        {"title": "Oil market update", "region": "Middle East", "provider": "gdelt", "source_status": "cached", "source_url": "https://example.test/news-2"},
    ]

    contract = build_map_news_event_fusion_contract(
        war_room_map=marker,
        news_dashboard={"normalized_news": news},
        event_graph={"nodes": [], "edges": []},
        provider_health=[],
        layer_runtime=_layer_payload(),
        market_intelligence={},
    )

    assert contract["news_rows"] == news
    assert all(row.get("source_url") for row in contract["news_rows"])


def test_nextjs_map_product_has_url_state_renderer_evidence_and_failure_path():
    page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    map_component = (ROOT / "apps/web/src/components/LeafletWarMap.tsx").read_text(encoding="utf-8")
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    for marker in [
        'requestedView === "war-room-map"',
        'data-product-view="global-risk-map"',
        "function GlobalRiskMapProduct",
        'active="war-map"',
    ]:
        assert marker in page

    for marker in [
        "useSearchParams",
        "window.history.replaceState",
        "data-map-state={mapState}",
        "data-map-marker-count={String(renderedMarkerCount)}",
        'params.set("layers"',
        'params.set("timeline"',
        'params.set("event"',
        'params.set("compare"',
        'searchParams.get("mapMode") === "fallback"',
        "relatedNews",
        "connectedAssets",
        "clusterMarkers",
    ]:
        assert marker in map_component
    assert "useRouter" not in map_component

    for selector in [
        ".global-risk-map-product",
        ".global-map-stage",
        ".global-map-overlay",
        ".global-event-inspector",
        ".global-map-mobile-drawer",
    ]:
        assert selector in css
