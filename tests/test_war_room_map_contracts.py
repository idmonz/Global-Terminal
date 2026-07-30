from __future__ import annotations

import json
import re
from pathlib import Path

from backend.api import app as backend_app
from lib.api_contracts import API_CONTRACT_VERSION, build_api_war_room_map_payload, validate_api_payload
from lib.event_asset_graph import build_event_asset_graph_contract
from lib.war_room_map import WAR_ROOM_MAP_VERSION, build_war_room_map_contract
from scripts.export_api_fixtures import build_api_fixture_payloads, export_api_fixtures


FORBIDDEN_MARKER_LAYER_PHRASES = [
    r"\bbuy\b",
    r"\bsell\b",
    r"\bhold\b",
    r"\bexecute\s+order\b",
    r"\border\s+routing\b",
]


def _event_row(**overrides):
    row = {
        "event_id": "evt-phase4-red-sea",
        "timestamp": "2026-06-16T00:00:00+00:00",
        "title": "Red Sea shipping risk remains watch-listed",
        "summary": "Public source-backed map row for shipping, oil, and FX context.",
        "domain": "chokepoints",
        "severity": "high",
        "region": "Red Sea",
        "lat": 18.0,
        "lon": 39.0,
        "source": "phase4.fixture",
        "source_url": "https://example.test/phase-4/red-sea",
        "provider": "fixture",
        "fetched_at": "2026-06-16T00:00:00+00:00",
        "freshness": "fixture",
        "source_status": "fixture",
        "confidence": 0.62,
        "related_tickers": ["CL=F", "BZ=F"],
        "coordinate_method": "fixture_coordinates",
        "data_gap": "No live AIS or vessel-flow provider in this fixture.",
        "caveat": "Fixture row; not live vessel tracking.",
    }
    row.update(overrides)
    return row


def _layer_payload():
    return {
        "layers": [
            {
                "layer_id": "chokepoints",
                "label": "Energy Chokepoints",
                "domain": "energy",
                "source": "static chokepoint registry",
                "provider": "local",
                "availability": "limited",
                "row_count": 1,
                "requires_key": None,
                "source_status": "proxy/static",
                "freshness_status": "proxy/static",
                "latest_fetched_at": None,
                "caveat": "Static registry plus proxy risk; no live vessel tracking.",
                "recommended_action": "Treat as context only.",
            },
            {
                "layer_id": "flight_tracking_unavailable",
                "label": "OpenSky Flight Tracking",
                "domain": "osint",
                "source": "OpenSky /states/all",
                "provider": "opensky",
                "availability": "unavailable",
                "row_count": 0,
                "requires_key": "OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET",
                "source_status": "missing-key",
                "freshness_status": "missing-key",
                "latest_fetched_at": None,
                "caveat": "Displayed as live only after OpenSky OAuth2 credentials exist and the state-vector fetch succeeds.",
                "recommended_action": "Configure the optional provider key or keep the layer unavailable.",
            },
            {
                "layer_id": "sanctions",
                "label": "Sanctions",
                "domain": "geopolitical",
                "source": "OpenSanctions registry slot",
                "provider": "opensanctions",
                "availability": "unavailable",
                "row_count": 0,
                "requires_key": None,
                "source_status": "unavailable",
                "freshness_status": "unavailable",
                "latest_fetched_at": None,
                "caveat": "Registry-only in this slice; no live sanctions rows are fetched or displayed.",
                "recommended_action": "Keep the surface disabled or show an explicit unavailable state.",
            },
        ],
        "summary": {"layer_count": 3},
    }


def _provider_rows():
    return [
        {
            "provider": "opensky",
            "source": "OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET",
            "status": "missing-key",
            "availability": "unavailable",
            "row_count": 0,
            "fetched_at": None,
            "warning": "OpenSky remains unavailable until OAuth credentials and state-vector fetch succeed.",
            "error": "Missing optional provider credentials.",
            "recommended_action": "Keep flight layer unavailable.",
            "caveat": "No fake live flight tracking is exported.",
        }
    ]


def _encoded(value) -> str:
    return json.dumps(value, sort_keys=True)


def test_map_contract_builds_source_backed_markers_with_provenance_and_graph_links():
    events = [_event_row(coordinate_method="source_coordinates", source_status="live/fresh")]
    graph = build_event_asset_graph_contract(events=events, provider_rows=_provider_rows())
    contract = build_war_room_map_contract(
        events=events,
        layer_runtime=_layer_payload(),
        provider_rows=_provider_rows(),
        event_graph=graph,
    )
    marker = contract["markers"][0]

    assert contract["war_room_map_version"] == WAR_ROOM_MAP_VERSION
    assert marker["marker_id"].startswith("marker:")
    assert marker["provider"] == "fixture"
    assert marker["source_url"] == "https://example.test/phase-4/red-sea"
    assert marker["fetched_at"] == "2026-06-16T00:00:00+00:00"
    assert marker["coordinate_status"] == "source-backed"
    assert marker["coordinate_method"] == "source_coordinates"
    assert marker["not_financial_advice"] is True
    assert marker["layer_ids"]
    assert marker["related_asset_node_ids"]


def test_approximate_fixture_and_static_coordinates_are_labeled():
    events = [
        _event_row(event_id="evt-fixture", coordinate_method="fixture_coordinates"),
        _event_row(
            event_id="evt-static",
            title="Static Hormuz chokepoint watch point",
            coordinate_method="static_registry",
            source_status="static/proxy",
            source_url="local://static-chokepoints",
        ),
        _event_row(
            event_id="evt-approx",
            title="Policy risk around Taiwan",
            lat=23.7,
            lon=121.0,
            region="Asia",
            domain="geopolitical",
            coordinate_method="region_centroid",
            approximate_location=True,
            data_gap="Coordinates use an approximate regional centroid.",
        ),
    ]
    contract = build_war_room_map_contract(events=events, layer_runtime=_layer_payload(), provider_rows=_provider_rows())
    statuses = {marker["event_id"]: marker["coordinate_status"] for marker in contract["markers"]}

    assert statuses["evt-fixture"] == "fixture"
    assert statuses["evt-static"] == "static/proxy"
    assert statuses["evt-approx"] == "approximate"
    assert contract["summary"]["fixture_coordinate_count"] == 1
    assert contract["summary"]["static_coordinate_count"] == 1
    assert contract["summary"]["approximate_coordinate_count"] == 1
    assert all(marker["data_gap"] for marker in contract["markers"] if marker["coordinate_status"] != "source-backed")


def test_missing_key_and_unavailable_layers_never_become_live_claims():
    contract = build_war_room_map_contract(
        events=[_event_row()],
        layer_runtime=_layer_payload(),
        provider_rows=_provider_rows(),
    )
    layers = {row["layer_id"]: row for row in contract["layers"]}
    requirements = {row["requirement_id"]: row for row in contract["provider_requirements"]}

    assert layers["flight_tracking_unavailable"]["availability"] == "unavailable"
    assert layers["flight_tracking_unavailable"]["source_status"] == "missing-key"
    assert layers["sanctions"]["availability"] == "unavailable"
    assert requirements["layer:flight_tracking_unavailable"]["live_claim_allowed"] is False
    assert requirements["capability:live_ais"]["live_claim_allowed"] is False
    assert requirements["capability:live_sanctions"]["live_claim_allowed"] is False
    assert contract["summary"]["live_ais_claimed"] is False
    assert contract["summary"]["live_flight_tracking_claimed"] is False
    assert contract["summary"]["live_sanctions_claimed"] is False


def test_timeline_filters_and_compare_windows_are_schema_ready_without_persistence():
    contract = build_war_room_map_contract(events=[_event_row()], layer_runtime=_layer_payload())

    assert {row["filter_id"] for row in contract["timeline_filters"]} >= {"1h", "24h", "48h", "7d", "all"}
    assert all(row["source_status"] == "schema-ready/offline-state" for row in contract["timeline_filters"])
    saved = next(row for row in contract["compare_windows"] if row["window_id"] == "saved_compare_session")
    assert saved["available"] is False
    assert saved["requires_persistence"] is True
    assert contract["readiness"]["hosted_persistence_added"] is False
    assert contract["readiness"]["auth_added"] is False
    assert contract["readiness"]["billing_added"] is False
    assert contract["readiness"]["graph_database_dependency_added"] is False


def test_natural_event_markers_keep_provider_specific_layers_and_coordinates():
    layer_payload = {
        "layers": [
            {
                "layer_id": "earthquakes",
                "label": "Earthquakes",
                "domain": "natural",
                "source": "USGS",
                "provider": "usgs_earthquake",
                "availability": "available",
                "row_count": 1,
                "requires_key": None,
                "source_status": "live/fresh",
                "freshness_status": "live/fresh",
                "latest_fetched_at": "2026-07-30T00:00:00+00:00",
                "caveat": "USGS source row.",
                "recommended_action": "Inspect source.",
            },
            {
                "layer_id": "fires",
                "label": "Wildfires",
                "domain": "natural",
                "source": "NASA EONET",
                "provider": "nasa_eonet",
                "availability": "available",
                "row_count": 1,
                "requires_key": None,
                "source_status": "live/fresh",
                "freshness_status": "live/fresh",
                "latest_fetched_at": "2026-07-30T00:00:00+00:00",
                "caveat": "EONET aggregation row.",
                "recommended_action": "Inspect EONET and upstream source.",
            },
        ]
    }
    events = [
        _event_row(
            event_id="EONET_FIRE",
            title="Current wildfire",
            domain="natural",
            provider="nasa_eonet",
            coordinate_method="nasa_eonet_geojson_point",
            layer_ids=["fires"],
            source_status="live/fresh",
        ),
        _event_row(
            event_id="USGS_QUAKE",
            title="M 5.4 earthquake",
            domain="natural",
            provider="usgs_earthquake",
            coordinate_method="usgs_geojson",
            layer_ids=["earthquakes"],
            source_status="live/fresh",
        ),
    ]

    contract = build_war_room_map_contract(events=events, layer_runtime=layer_payload)
    markers = {row["event_id"]: row for row in contract["markers"]}

    assert markers["EONET_FIRE"]["layer_ids"] == ["fires"]
    assert markers["EONET_FIRE"]["coordinate_status"] == "source-backed"
    assert markers["USGS_QUAKE"]["layer_ids"] == ["earthquakes"]


def test_default_map_bound_keeps_a_clusterable_multi_provider_event_surface():
    events = [
        _event_row(
            event_id=f"evt-{index}",
            title=f"Natural event {index}",
            domain="natural",
            provider="nasa_eonet" if index % 2 else "usgs_earthquake",
            layer_ids=["fires" if index % 2 else "earthquakes"],
            lat=-60 + (index % 120),
            lon=-170 + (index * 3) % 340,
            coordinate_method="nasa_eonet_geojson_point" if index % 2 else "usgs_geojson",
            source_status="live/fresh",
        )
        for index in range(180)
    ]

    contract = build_war_room_map_contract(events=events, layer_runtime={"layers": []})

    assert contract["summary"]["marker_count"] == 180



def test_war_room_map_api_payload_is_phase2b_json_safe_and_non_advisory():
    payload = build_api_war_room_map_payload(
        events=[_event_row(coordinate_method="source_coordinates", source_status="live/fresh")],
        layer_runtime=_layer_payload(),
        provider_rows=_provider_rows(),
    )
    marker_layer_text = _encoded(
        {
            "markers": payload["data"]["markers"],
            "layers": payload["data"]["layers"],
        }
    ).lower()

    assert payload["contract_version"] == API_CONTRACT_VERSION
    assert payload["payload_type"] == "war_room_map"
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    for phrase in FORBIDDEN_MARKER_LAYER_PHRASES:
        assert not re.search(phrase, marker_layer_text), phrase


def test_fixture_export_includes_war_room_map_and_keeps_fixture_safe(tmp_path):
    payloads = build_api_fixture_payloads()
    written = export_api_fixtures(tmp_path)

    assert "war-room-map.json" in payloads
    assert "war-room-map.json" in {path.name for path in written}
    fixture = payloads["war-room-map.json"]
    encoded = _encoded(fixture)

    assert fixture["payload_type"] == "war_room_map"
    assert fixture["summary"]["marker_count"] >= 1
    assert fixture["summary"]["broker_execution_added"] is False
    assert "\\data\\private\\" not in encoded
    assert ".env" not in encoded
    valid, issues = validate_api_payload(fixture)
    assert valid, issues


def test_backend_optional_war_room_map_getter_is_valid():
    payload = backend_app.get_war_room_map_payload()

    assert payload["payload_type"] == "war_room_map"
    valid, issues = validate_api_payload(payload)
    assert valid, issues


def test_web_fixture_validator_knows_war_room_map_fixture():
    validator = Path("apps/web/scripts/validate-fixtures.mjs").read_text(encoding="utf-8")

    assert "war-room-map.json" in validator
    assert "war_room_map" in validator


def test_source_coordinates_can_add_a_transparent_broad_region_when_provider_region_is_global():
    contract = build_war_room_map_contract(
        events=[
            _event_row(
                event_id="evt-papua",
                title="M 5.4 - near Papua New Guinea",
                domain="natural",
                region="Global",
                lat=-5.5,
                lon=151.2,
                coordinate_method="usgs_geojson",
                source_status="live/fresh",
            )
        ],
        layer_runtime=_layer_payload(),
    )
    marker = contract["markers"][0]

    assert marker["region"] == "Oceania"
    assert marker["region_method"] == "coordinate-derived-broad-region"
    assert marker["coordinate_status"] == "source-backed"


def test_nan_provider_region_is_treated_as_missing_and_derived_from_coordinates():
    contract = build_war_room_map_contract(
        events=[
            _event_row(
                event_id="evt-empty-region",
                domain="natural",
                region=float("nan"),
                lat=44.0,
                lon=-120.5,
                coordinate_method="nasa_eonet_geojson_point",
                source_status="live/fresh",
            )
        ],
        layer_runtime=_layer_payload(),
    )

    marker = contract["markers"][0]
    assert marker["region"] == "Americas"
    assert marker["region_method"] == "coordinate-derived-broad-region"


def test_backend_map_requests_the_full_clusterable_event_bound(monkeypatch):
    observed: dict[str, int] = {}

    def fake_war_room_payload(*, include_runtime=False, max_events=100):
        observed["max_events"] = max_events
        return {"data": {"events": [], "layer_runtime_status": {"layers": []}}}

    monkeypatch.setattr(backend_app, "get_war_room_payload", fake_war_room_payload)
    monkeypatch.setattr(backend_app, "get_provider_health_payload", lambda: {"data": []})
    monkeypatch.setattr(backend_app, "get_event_asset_graph_payload", lambda **_: {"data": {}})

    payload = backend_app.get_war_room_map_payload(include_runtime=True)

    assert observed["max_events"] == 400
    assert payload["payload_type"] == "war_room_map"
