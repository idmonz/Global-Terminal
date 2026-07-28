from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from backend.api import app as backend_app
from lib.api_contract_panels import contract_collection_rows, contract_preview, contract_summary_rows
from lib.api_contracts import (
    API_CONTRACT_VERSION,
    build_api_ai_provider_payload,
    build_api_asset_universe_payload,
    build_api_command_workspace_payload,
    build_api_crypto_intelligence_payload,
    build_api_equity_intelligence_payload,
    build_api_feed_registry_payload,
    build_api_financial_fundamentals_payload,
    build_api_layer_runtime_payload,
    build_api_market_intelligence_payload,
    build_api_news_dashboard_payload,
    build_api_options_quant_payload,
    build_api_product_parity_payload,
    build_api_provider_health_payload,
    build_api_route_manifest_payload,
    build_api_screener_drilldown_payload,
    build_api_war_room_payload,
    build_api_war_room_map_payload,
    to_json_safe,
    validate_api_payload,
)
from lib.data_status import error_result, ok_result
from lib.news_intelligence import build_worldmonitor_style_news_dashboard
from lib.war_room import build_war_room_state


def _assert_valid(payload: dict) -> None:
    assert payload["contract_version"] == API_CONTRACT_VERSION
    json.dumps(payload)
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    assert not _contains_dataframe(payload)


def _contains_dataframe(value) -> bool:
    if isinstance(value, (pd.DataFrame, pd.Series, pd.Timestamp)):
        return True
    if isinstance(value, dict):
        return any(_contains_dataframe(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_dataframe(item) for item in value)
    return False


def _contains_key(value, target: str) -> bool:
    if isinstance(value, dict):
        return any(str(key) == target or _contains_key(item, target) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_key(item, target) for item in value)
    return False


def _event_row(**overrides):
    base = {
        "title": "Oil tankers reroute after missile attack near Strait of Hormuz",
        "summary": "Public source-backed event.",
        "source": "reuters.com",
        "source_url": "https://example.test/news",
        "provider": "gdelt",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "freshness": "fresh",
        "source_status": "fresh",
        "confidence": 0.7,
        "lat": 26.56,
        "lon": 56.25,
        "coordinate_method": "named_location",
        "data_gap": "",
        "caveat": "Unit-test public feed row.",
    }
    base.update(overrides)
    return base


def test_json_safe_sanitizer_converts_runtime_objects_and_redacts_secrets():
    frame = pd.DataFrame([{"timestamp": pd.Timestamp("2026-06-16T00:00:00Z"), "value": 1.5}])
    payload = to_json_safe(
        {
            "frame": frame,
            "fetched_at": datetime(2026, 6, 16, tzinfo=timezone.utc),
            "access_token": "secret-token",
            "env_var": "GEMINI_API_KEY",
        }
    )

    assert payload["frame"][0]["timestamp"].startswith("2026-06-16")
    assert payload["fetched_at"].startswith("2026-06-16")
    assert payload["access_token"] == "[redacted]"
    assert payload["env_var"] == "GEMINI_API_KEY"
    json.dumps(payload)


def test_feed_registry_api_payload_is_stable_and_json_safe():
    payload = build_api_feed_registry_payload()

    _assert_valid(payload)
    assert payload["payload_type"] == "feed_registry"
    assert payload["summary"]["feed_count"] >= 1
    assert "news_osint" in payload["summary"]["categories"]
    assert any(row["provider"] == "opensky" for row in payload["unavailable"])


def test_provider_health_api_payload_counts_rows_without_dataframe_leakage():
    status = ok_result(pd.DataFrame([{"title": "row"}]), source="RSS", provider="rss", coverage="1 row")
    missing = error_result(
        source="OPENSKY_CLIENT_ID,OPENSKY_CLIENT_SECRET",
        provider="opensky",
        error="Missing optional environment variable: OPENSKY_CLIENT_ID or OPENSKY_CLIENT_SECRET",
        is_paid_required=True,
    )

    payload = build_api_provider_health_payload([status, missing])

    _assert_valid(payload)
    assert payload["payload_type"] == "provider_health"
    assert payload["summary"]["provider_count"] == 2
    assert payload["data"][0]["row_count"] == 1
    assert any(row["status"] == "missing-key" for row in payload["data"])


def test_layer_runtime_api_payload_preserves_live_timestamp_and_unavailable_layers():
    fetched = datetime.now(timezone.utc).isoformat()
    runtime = {
        "natural": [
            {
                "title": "M 5.4 earthquake",
                "provider": "usgs_earthquake",
                "source": "USGS",
                "source_url": "https://earthquake.usgs.gov/event/test",
                "fetched_at": fetched,
                "freshness": "fresh",
                "source_status": "fresh",
                "lat": 1.0,
                "lon": 2.0,
            }
        ]
    }
    status = ok_result([], source="USGS", provider="usgs_earthquake", coverage="1 row")

    payload = build_api_layer_runtime_payload(runtime_feeds=runtime, statuses=[status])

    _assert_valid(payload)
    layers = payload["data"]["layers"]
    earthquakes = next(row for row in layers if row["layer_id"] == "earthquakes")
    flight = next(row for row in layers if row["layer_id"] == "flight_tracking_unavailable")

    assert earthquakes["source_status"] == "live/fresh"
    assert earthquakes["latest_fetched_at"]
    assert flight["availability"] == "unavailable"


def test_news_dashboard_api_payload_serializes_dataframes_to_records():
    dashboard = build_worldmonitor_style_news_dashboard(
        [_event_row()],
        [ok_result([], source="GDELT", provider="gdelt", coverage="1 row")],
    )

    payload = build_api_news_dashboard_payload(dashboard=dashboard)

    _assert_valid(payload)
    assert payload["payload_type"] == "news_dashboard"
    assert isinstance(payload["data"]["normalized_news"], list)
    assert payload["data"]["normalized_news"][0]["provider"] == "gdelt"
    assert payload["summary"]["status"] == "available"


def test_news_dashboard_api_payload_accepts_dataframe_items_directly():
    items = pd.DataFrame([_event_row()])

    payload = build_api_news_dashboard_payload(
        items,
        [ok_result(items, source="GDELT", provider="gdelt", coverage="1 row")],
    )

    _assert_valid(payload)
    assert payload["data"]["normalized_news"][0]["provider"] == "gdelt"


def test_war_room_api_payload_omits_plotly_and_streamlit_runtime_objects():
    state = build_war_room_state(news=[_event_row()], include_default_runtime=False)

    payload = build_api_war_room_payload(state)

    _assert_valid(payload)
    assert payload["payload_type"] == "war_room"
    assert not _contains_key(payload, "fig")
    assert not _contains_key(payload, "chokepoint_fig")
    assert payload["data"]["map_summary"]["event_row_count"] >= 1
    assert payload["data"]["events"]
    assert payload["summary"]["event_count"] >= 1


def test_ai_provider_api_payload_is_free_first_and_never_exposes_keys(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_test_secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-paid")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_ENABLE_GOOGLE_SEARCH", raising=False)

    payload = build_api_ai_provider_payload()
    encoded = json.dumps(payload)

    _assert_valid(payload)
    assert payload["payload_type"] == "ai_provider_status"
    assert payload["summary"]["selected_provider"] == "gemini"
    assert payload["summary"]["selected_free_mode"] is True
    assert payload["summary"]["openai_api_key_required"] is False
    assert payload["summary"]["gemini_google_search_grounding_enabled"] is False
    assert "AIza_test_secret" not in encoded
    assert "sk-ant-paid" not in encoded
    assert "GEMINI_API_KEY" in encoded


def test_asset_universe_api_payload_adds_reference_schema_without_live_claims():
    payload = build_api_asset_universe_payload()

    _assert_valid(payload)
    assert payload["payload_type"] == "asset_universe"
    assert payload["summary"]["reference_project"] == "FinanceDatabase"
    assert payload["summary"]["live_rows_claimed"] is False
    assert payload["summary"]["external_rows_copied"] is False
    assert any(row["asset_class"] == "crypto_pair" for row in payload["data"]["asset_classes"])


def test_command_workspace_api_payload_is_provider_gated_and_route_ready():
    payload = build_api_command_workspace_payload()

    _assert_valid(payload)
    assert payload["payload_type"] == "command_workspace"
    assert payload["summary"]["broker_execution_added"] is False
    assert payload["summary"]["hosted_persistence_added"] is False
    assert any(row["command"] == "NI" for row in payload["data"]["commands"])
    assert all(row["not_financial_advice"] is True for row in payload["data"]["commands"])


def test_war_room_map_api_payload_adds_map_first_contract_without_live_claims():
    state = build_war_room_state(news=[_event_row()], include_default_runtime=False)
    payload = build_api_war_room_map_payload(state=state)

    _assert_valid(payload)
    assert payload["payload_type"] == "war_room_map"
    assert payload["data"]["markers"]
    assert payload["data"]["timeline_filters"]
    assert payload["data"]["compare_windows"]
    assert payload["summary"]["live_ais_claimed"] is False
    assert payload["summary"]["broker_execution_added"] is False
    assert all(row["not_financial_advice"] is True for row in payload["data"]["markers"])


def test_phase5a_workstation_api_payloads_are_json_safe_source_labeled_and_non_advisory():
    payloads = [
        build_api_product_parity_payload(),
        build_api_market_intelligence_payload(include_runtime=False),
        build_api_equity_intelligence_payload(symbol="AAPL", include_runtime=False),
        build_api_financial_fundamentals_payload(symbol="AAPL", include_runtime=False),
        build_api_options_quant_payload(symbol="AAPL", include_runtime=False),
        build_api_screener_drilldown_payload(include_runtime=False),
        build_api_crypto_intelligence_payload(symbol="BTCUSDT", include_runtime=False),
    ]

    for payload in payloads:
        _assert_valid(payload)
        assert payload["summary"]["non_advisory"] is True
        assert payload["source_status"]
        assert payload["caveats"]

    assert payloads[1]["data"]["workspace"] == "market-intelligence"
    assert payloads[2]["data"]["workspace"] == "equity-intelligence"
    assert payloads[3]["data"]["workspace"] == "financial-fundamentals"
    assert payloads[4]["data"]["workspace"] == "options-quant"
    assert payloads[5]["data"]["workspace"] == "screener-drilldown"
    assert payloads[6]["data"]["workspace"] == "crypto-intelligence"


def test_optional_backend_module_is_import_safe_without_requiring_fastapi():
    manifest = backend_app.get_api_manifest()
    product_parity = backend_app.get_product_parity_payload()
    market_intelligence = backend_app.get_market_intelligence_payload()
    equity_intelligence = backend_app.get_equity_intelligence_payload()
    financial_fundamentals = backend_app.get_financial_fundamentals_payload()
    options_quant = backend_app.get_options_quant_payload()
    screener_drilldown = backend_app.get_screener_drilldown_payload()
    crypto_intelligence = backend_app.get_crypto_intelligence_payload()
    feeds = backend_app.get_feeds_payload()
    asset_universe = backend_app.get_asset_universe_payload()
    command_workspace = backend_app.get_command_workspace_payload()
    war_room_map = backend_app.get_war_room_map_payload()
    direct_manifest = build_api_route_manifest_payload(fastapi_available=backend_app.FASTAPI_AVAILABLE)

    _assert_valid(manifest)
    _assert_valid(product_parity)
    _assert_valid(market_intelligence)
    _assert_valid(equity_intelligence)
    _assert_valid(financial_fundamentals)
    _assert_valid(options_quant)
    _assert_valid(screener_drilldown)
    _assert_valid(crypto_intelligence)
    _assert_valid(feeds)
    _assert_valid(asset_universe)
    _assert_valid(command_workspace)
    _assert_valid(war_room_map)
    _assert_valid(direct_manifest)
    assert manifest["summary"]["base_streamlit_ui_preserved"] is True
    assert backend_app.app is None if not backend_app.FASTAPI_AVAILABLE else backend_app.app is not None


def test_contract_panel_helpers_return_compact_json_safe_summaries():
    payload = build_api_feed_registry_payload()

    rows = contract_summary_rows(payload)
    preview = contract_preview(payload)
    collection = contract_collection_rows([payload, build_api_route_manifest_payload()])

    assert any(row["metric"] == "payload_type" and row["value"] == "feed_registry" for row in rows)
    assert preview["payload_type"] == "feed_registry"
    assert preview["unavailable_count"] == len(payload["unavailable"])
    assert collection[0]["payload_type"] == "feed_registry"
    json.dumps({"rows": rows, "preview": preview, "collection": collection})
