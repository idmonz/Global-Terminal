from __future__ import annotations

from datetime import datetime, timezone

from lib.data_status import error_result, ok_result
from lib.war_room import build_data_gap_panel, build_war_room_ai_context, build_war_room_header_metrics, build_war_room_state


def _runtime_row(**overrides):
    base = {
        "title": "M 5.6 earthquake near test coast",
        "summary": "Official source-backed event.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "domain": "natural",
        "severity": "elevated",
        "region": "Global",
        "lat": 1.0,
        "lon": 2.0,
        "provider": "usgs_earthquake",
        "source": "USGS Earthquake Hazards Program",
        "source_url": "https://earthquake.usgs.gov/event/test",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "freshness": "fresh",
        "source_status": "fresh",
        "confidence": 0.95,
        "coordinate_method": "usgs_geojson",
        "data_gap": "",
        "caveat": "USGS events can revise after initial publication.",
    }
    base.update(overrides)
    return base


def test_war_room_state_contains_required_surfaces():
    state = build_war_room_state(news=[{"title": "Taiwan semiconductor export controls", "region": "Asia", "severity": "high"}])
    assert state["map_payload"]
    assert state["right_rail"]["event_cards"]
    assert "source_status" in state
    assert "market_impact_summary" in state
    assert state["header_metrics"]["global_risk_state"] in {"low", "watch", "elevated", "high", "critical"}


def test_war_room_ai_context_and_data_gaps():
    state = build_war_room_state(news=[])
    context = build_war_room_ai_context(state)
    assert context["not_financial_advice"] is True
    assert context["verify_primary_data"] is True
    gaps = build_data_gap_panel(state)
    assert not gaps.empty
    header = build_war_room_header_metrics(state)
    assert "command_modes" in header


def test_war_room_default_runtime_adds_source_backed_rows(monkeypatch):
    def fake_runtime(**_kwargs):
        return {
            "news": [_runtime_row(title="Red Sea shipping risk", domain="shipping", provider="gdelt", source_url="https://example.test/news")],
            "natural": [_runtime_row()],
            "crypto": [_runtime_row(title="BTC public crypto market state", domain="crypto", provider="coingecko_public", coordinate_method="not_applicable")],
            "source_statuses": [ok_result([], source="unit", provider="unit", coverage="3 rows")],
            "source_status": [],
            "data_gaps": [],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "caveat": "unit",
        }

    monkeypatch.setattr("lib.war_room.build_keyless_runtime_feeds", fake_runtime)
    state = build_war_room_state(include_default_runtime=True)

    providers = {event["provider"] for event in state["events"]}
    assert {"gdelt", "usgs_earthquake", "coingecko_public"}.issubset(providers)
    assert any(event["provider"] != "local" for event in state["events"])


def test_war_room_runtime_failure_is_explicit_not_fake_live(monkeypatch):
    def fake_runtime(**_kwargs):
        return {
            "news": [],
            "natural": [],
            "crypto": [],
            "source_statuses": [error_result(source="USGS", provider="usgs_earthquake", error="timeout")],
            "source_status": [],
            "data_gaps": ["usgs_earthquake: timeout"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "caveat": "unit",
        }

    monkeypatch.setattr("lib.war_room.build_keyless_runtime_feeds", fake_runtime)
    state = build_war_room_state(include_default_runtime=True)

    assert state["header_metrics"]["data_freshness_summary"] == "data gap"
    assert state["source_status"]["status"].astype(str).str.contains("error").any()
    assert all(event["provider"] == "local" for event in state["events"])


def test_war_room_event_rows_carry_provenance(monkeypatch):
    def fake_runtime(**_kwargs):
        return {
            "news": [],
            "natural": [_runtime_row()],
            "crypto": [],
            "source_statuses": [ok_result([], source="USGS", provider="usgs_earthquake", coverage="1 row")],
            "source_status": [],
            "data_gaps": [],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "caveat": "unit",
        }

    monkeypatch.setattr("lib.war_room.build_keyless_runtime_feeds", fake_runtime)
    state = build_war_room_state(include_default_runtime=True)
    required = {"provider", "source_url", "fetched_at", "freshness", "source_status", "confidence", "coordinate_method", "data_gap", "caveat"}

    assert state["events"]
    for event in state["events"]:
        assert required.issubset(event)
