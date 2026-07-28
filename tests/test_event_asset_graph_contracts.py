from __future__ import annotations

import json

from backend.api import app as backend_app
from lib.api_contracts import API_CONTRACT_VERSION, build_api_event_asset_graph_payload, validate_api_payload
from lib.event_asset_graph import build_event_asset_graph_contract
from scripts.export_api_fixtures import build_api_fixture_payloads, export_api_fixtures


def _source_event(**overrides):
    row = {
        "event_id": "evt-red-sea-fixture",
        "timestamp": "2026-06-16T00:00:00+00:00",
        "title": "Red Sea shipping risk keeps tanker route pressure elevated",
        "summary": "Public feed row linking shipping, oil, global trade, FX risk, and command routing.",
        "domain": "chokepoints",
        "severity": "high",
        "region": "Red Sea",
        "source": "phase2f.fixture",
        "source_url": "https://example.test/phase-2f/red-sea",
        "provider": "fixture",
        "fetched_at": "2026-06-16T00:00:00+00:00",
        "freshness": "fixture",
        "source_status": "fixture",
        "confidence": 0.62,
        "related_tickers": ["CL=F", "BZ=F"],
        "coordinate_method": "fixture_coordinates",
        "data_gap": "No live AIS or vessel-flow provider in this fixture.",
        "caveat": "Static fixture row; not live vessel tracking.",
    }
    row.update(overrides)
    return row


def _provider_row(**overrides):
    row = {
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
    row.update(overrides)
    return row


def test_event_asset_graph_contract_links_source_events_to_cross_asset_nodes():
    graph = build_event_asset_graph_contract(events=[_source_event()], provider_rows=[_provider_row()])

    node_ids = {node["id"] for node in graph["nodes"]}
    edge_pairs = {(edge["source"], edge["target"], edge["relationship"]) for edge in graph["edges"]}

    assert "event:evt-red-sea-fixture" in node_ids
    assert "region:red-sea" in node_ids
    assert "sector:energy" in node_ids
    assert "commodity:brent-crude" in node_ids
    assert "commodity:wti-crude" in node_ids
    assert "fx_pair:usdjpy" in node_ids
    assert "asset_class:fx_pair" in node_ids
    assert "asset_class:crypto_pair" in node_ids
    assert "command:NI" in node_ids
    assert ("event:evt-red-sea-fixture", "region:red-sea", "located_in") in edge_pairs
    assert ("event:evt-red-sea-fixture", "commodity:brent-crude", "affects") in edge_pairs
    assert ("event:evt-red-sea-fixture", "command:NI", "routes_to") in edge_pairs
    assert graph["summary"]["event_node_count"] == 1
    assert graph["summary"]["persistence_status"] == "unavailable"


def test_graph_nodes_and_edges_carry_provenance_confidence_and_caveats():
    graph = build_event_asset_graph_contract(events=[_source_event()], provider_rows=[_provider_row()])

    required_node_fields = {
        "id",
        "type",
        "label",
        "source_status",
        "confidence",
        "provider",
        "source_url",
        "fetched_at",
        "caveat",
        "data_gap",
    }
    required_edge_fields = {
        "id",
        "source",
        "target",
        "relationship",
        "confidence",
        "source_status",
        "evidence",
        "caveat",
    }

    assert graph["nodes"]
    assert graph["edges"]
    assert all(required_node_fields.issubset(node) for node in graph["nodes"])
    assert all(required_edge_fields.issubset(edge) for edge in graph["edges"])
    inferred_edges = [edge for edge in graph["edges"] if edge["source_status"] == "inferred/proxy"]
    assert inferred_edges
    assert all(0 < float(edge["confidence"]) < 1 for edge in inferred_edges)
    assert all(edge["caveat"] for edge in inferred_edges)


def test_graph_readiness_keeps_live_persistence_unavailable():
    graph = build_event_asset_graph_contract(events=[_source_event()], provider_rows=[_provider_row()])

    readiness = graph["readiness"]
    assert readiness["graph_persistence"]["status"] == "unavailable"
    assert readiness["live_store"]["status"] == "unavailable"
    assert readiness["graph_database_dependency_added"] is False
    assert readiness["hosted_supabase_dependency_added"] is False
    assert any(row["capability"] == "live_graph_persistence" for row in readiness["unavailable_capabilities"])


def test_event_asset_graph_api_payload_validates_and_keeps_asset_schema_reference_only():
    payload = build_api_event_asset_graph_payload(events=[_source_event()], provider_rows=[_provider_row()])

    assert payload["contract_version"] == API_CONTRACT_VERSION
    assert payload["payload_type"] == "event_asset_graph"
    assert payload["summary"]["external_rows_copied"] is False
    assert payload["summary"]["live_graph_persistence"] is False
    assert payload["summary"]["asset_schema_mode"] == "reference-schema"
    assert any(row["external_project"] == "FinanceDatabase" for row in payload["data"]["evidence_refs"])

    valid, issues = validate_api_payload(payload)
    assert valid, issues
    encoded = json.dumps(payload, sort_keys=True)
    assert "AAPL" not in encoded
    assert "FinanceDatabase-main/database/equities/NMS.csv:1-1" in encoded


def test_static_fixture_export_includes_event_asset_graph(tmp_path):
    payloads = build_api_fixture_payloads()
    written = export_api_fixtures(tmp_path)

    assert "event-asset-graph.json" in payloads
    assert "event-asset-graph.json" in {path.name for path in written}
    fixture = payloads["event-asset-graph.json"]
    assert fixture["payload_type"] == "event_asset_graph"
    assert fixture["summary"]["persistence_status"] == "unavailable"
    valid, issues = validate_api_payload(fixture)
    assert valid, issues


def test_backend_optional_event_asset_graph_getter_is_valid():
    payload = backend_app.get_event_asset_graph_payload()

    assert payload["payload_type"] == "event_asset_graph"
    valid, issues = validate_api_payload(payload)
    assert valid, issues
