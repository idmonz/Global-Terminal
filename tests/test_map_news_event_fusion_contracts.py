from __future__ import annotations

import json
import re

from backend.api import app as backend_app
from lib.api_contracts import API_CONTRACT_VERSION, build_api_map_news_event_fusion_payload, validate_api_payload
from lib.map_news_event_fusion import MAP_NEWS_EVENT_FUSION_VERSION, build_map_news_event_fusion_contract
from scripts.export_api_fixtures import build_api_fixture_payloads, export_api_fixtures


FORBIDDEN_FUSION_PHRASES = [
    r"\bbuy\b",
    r"\bsell\b",
    r"\bexecute\s+order\b",
    r"\border\s+routing\b",
]


def _fixture_inputs():
    payloads = build_api_fixture_payloads()
    return {
        "war_room_map": payloads["war-room-map.json"]["data"],
        "news_dashboard": payloads["news.json"]["data"],
        "event_graph": payloads["event-asset-graph.json"]["data"],
        "provider_health": payloads["provider-health.json"],
        "layer_runtime": payloads["layers.json"]["data"],
        "market_intelligence": payloads["market-intelligence.json"]["data"],
    }


def test_fusion_contract_links_marker_news_graph_provider_layer_and_heatmap_context():
    contract = build_map_news_event_fusion_contract(**_fixture_inputs())

    assert contract["map_news_event_fusion_version"] == MAP_NEWS_EVENT_FUSION_VERSION
    assert contract["workspace"] == "map-news-event-fusion"
    assert contract["markers"]
    assert contract["selected_marker"]
    assert contract["related_news"]
    assert contract["event_links"]
    assert contract["connected_assets"]
    assert contract["heatmap_context"]
    assert contract["layer_health"]
    assert contract["provider_health"]
    assert contract["source_register"]
    assert contract["summary"]["heatmap_context_count"] == len(contract["heatmap_context"])
    assert contract["summary"]["non_advisory"] is True


def test_fusion_rows_preserve_source_truth_and_do_not_claim_fake_live():
    contract = build_map_news_event_fusion_contract(**_fixture_inputs())

    assert contract["readiness"]["broker_execution_added"] is False
    assert contract["readiness"]["auth_added"] is False
    assert contract["readiness"]["billing_added"] is False
    assert contract["readiness"]["external_source_copied"] is False
    assert contract["readiness"]["live_claim_allowed"] is False
    assert contract["unavailable_sources"]
    assert all(row["source_status"] for row in contract["source_register"])
    assert all(row.get("not_financial_advice") is True for row in contract["related_news"])
    assert all(row.get("not_financial_advice") is True for row in contract["event_links"])
    assert all(row.get("not_financial_advice") is True for row in contract["heatmap_context"])


def test_fusion_api_payload_is_phase2b_json_safe_and_non_advisory():
    payload = build_api_map_news_event_fusion_payload(**_fixture_inputs())
    encoded = json.dumps(payload, sort_keys=True).lower()

    assert payload["contract_version"] == API_CONTRACT_VERSION
    assert payload["payload_type"] == "map_news_event_fusion"
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    for phrase in FORBIDDEN_FUSION_PHRASES:
        assert not re.search(phrase, encoded), phrase
    assert "market_heatmap" in encoded
    assert "map-news-event" in encoded


def test_fixture_export_includes_map_news_event_fusion_and_keeps_fixture_safe(tmp_path):
    payloads = build_api_fixture_payloads()
    written = export_api_fixtures(tmp_path)

    assert "map-news-event-fusion.json" in payloads
    assert "map-news-event-fusion.json" in {path.name for path in written}
    fixture = payloads["map-news-event-fusion.json"]
    encoded = json.dumps(fixture, sort_keys=True)

    assert fixture["payload_type"] == "map_news_event_fusion"
    assert fixture["data"]["heatmap_context"]
    assert "\\data\\private\\" not in encoded
    assert ".env" not in encoded
    valid, issues = validate_api_payload(fixture)
    assert valid, issues


def test_backend_optional_map_news_event_fusion_getter_is_valid():
    payload = backend_app.get_map_news_event_fusion_payload()

    assert payload["payload_type"] == "map_news_event_fusion"
    valid, issues = validate_api_payload(payload)
    assert valid, issues


def test_fusion_uses_the_complete_normalized_news_feed_not_only_the_high_severity_subset():
    inputs = _fixture_inputs()
    inputs["news_dashboard"] = {
        "normalized_news": [
            {
                "title": "Red Sea shipping rates rise as carriers reroute",
                "provider": "rss",
                "source_url": "https://example.test/red-sea-shipping",
                "source_status": "live/fresh",
                "freshness": "fresh",
                "region": "Red Sea",
            },
            {
                "title": "Earthquake response continues near Japan",
                "provider": "rss",
                "source_url": "https://example.test/japan-earthquake",
                "source_status": "live/fresh",
                "freshness": "fresh",
                "region": "Asia",
            },
        ],
        "high_severity_feed": [
            {
                "title": "Red Sea shipping rates rise as carriers reroute",
                "provider": "rss",
                "source_url": "https://example.test/red-sea-shipping",
                "source_status": "live/fresh",
                "freshness": "fresh",
                "region": "Red Sea",
            }
        ],
    }

    contract = build_map_news_event_fusion_contract(**inputs)

    assert {row["source_url"] for row in contract["news_rows"]} == {
        "https://example.test/red-sea-shipping",
        "https://example.test/japan-earthquake",
    }


def test_fusion_builds_bounded_direct_context_for_every_marker():
    contract = build_map_news_event_fusion_contract(**_fixture_inputs())
    contexts = contract["event_contexts"]

    assert len(contexts) == len(contract["markers"])
    assert contract["selected_marker_id"] in {row["marker_id"] for row in contexts}
    for context in contexts:
        event_node_id = context.get("event_graph_node_id")
        assert context["context_status"] in {"source-linked", "taxonomy-linked", "event-only"}
        assert context["not_financial_advice"] is True
        for link in context["event_links"]:
            assert event_node_id in {link.get("source"), link.get("target")}
            assert link.get("node_type") != "event"


def test_fusion_news_matches_explain_exact_region_or_topic_context_without_claiming_causality():
    inputs = _fixture_inputs()
    marker = inputs["war_room_map"]["markers"][0]
    inputs["news_dashboard"] = {
        "normalized_news": [
            {
                "title": f"Reporting update for {marker['title']}",
                "provider": "rss",
                "source_url": "https://example.test/exact-marker-report",
                "source_status": "live/fresh",
                "freshness": "fresh",
                "region": marker.get("region"),
            }
        ]
    }

    contract = build_map_news_event_fusion_contract(**inputs)
    context = next(row for row in contract["event_contexts"] if row["marker_id"] == marker["marker_id"])

    assert context["related_news"]
    assert context["related_news"][0]["match_method"] in {"source-url", "title", "region", "domain-keyword"}
    assert "not proof of causality" in context["related_news"][0]["match_caveat"].lower()


def test_coordinate_derived_broad_region_does_not_create_false_news_match():
    inputs = _fixture_inputs()
    marker = inputs["war_room_map"]["markers"][0]
    marker["region"] = "Americas"
    marker["region_method"] = "coordinate-derived-broad-region"
    marker["domain"] = "natural"
    inputs["news_dashboard"] = {
        "normalized_news": [
            {
                "title": "Central bank publishes routine balance sheet",
                "provider": "rss",
                "source_url": "https://example.test/routine-balance-sheet",
                "source_status": "live/fresh",
                "freshness": "fresh",
                "region": "Americas",
            }
        ]
    }

    contract = build_map_news_event_fusion_contract(**inputs)
    context = next(row for row in contract["event_contexts"] if row["marker_id"] == marker["marker_id"])

    assert context["related_news"] == []


def test_single_generic_domain_keyword_does_not_create_related_reporting():
    inputs = _fixture_inputs()
    marker = inputs["war_room_map"]["markers"][0]
    marker["domain"] = "chokepoints"
    marker["region"] = "Middle East"
    marker["region_method"] = "coordinate-derived-broad-region"
    inputs["news_dashboard"] = {
        "normalized_news": [
            {
                "title": "California natural gas energy prices change",
                "provider": "rss",
                "source_url": "https://example.test/california-gas",
                "source_status": "live/fresh",
                "freshness": "fresh",
                "region": "Americas",
            }
        ]
    }

    contract = build_map_news_event_fusion_contract(**inputs)
    context = next(row for row in contract["event_contexts"] if row["marker_id"] == marker["marker_id"])

    assert context["related_news"] == []


def test_unavailable_sources_are_deduplicated_by_provider_layer_and_status():
    inputs = _fixture_inputs()
    duplicate = {
        "provider": "opensky",
        "source": "OpenSky",
        "status": "missing-key",
        "availability": "unavailable",
        "caveat": "No verified flight rows.",
    }
    inputs["provider_health"] = {"data": [duplicate, dict(duplicate)]}

    contract = build_map_news_event_fusion_contract(**inputs)

    opensky_rows = [
        row
        for row in contract["unavailable_sources"]
        if row.get("provider") == "opensky" and row.get("status") == "missing-key" and not row.get("layer_id")
    ]
    assert len(opensky_rows) == 1
