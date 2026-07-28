from datetime import datetime, timezone

from lib.hotspot_panel import build_hotspot_panel
from lib.intel_feed_engine import build_event_risk_label, build_event_time_window_filter, build_intel_feed
from lib.layer_panel_payload import build_layer_panel_payload
from lib.osint_locate_actions import build_locate_action_payload
from lib.view_preset_engine import build_view_presets


def test_goal11c_intel_feed_presets_layers_and_risk_labels():
    events = [
        {"title": "Event A", "region": "Red Sea", "severity": "critical", "confidence": "high", "source": "supplied", "created_at": "2026-06-14T00:00:00+00:00", "lat": 1, "lon": 2},
        {"title": "Event B", "region": "Red Sea", "severity": "critical", "confidence": "low", "source": "supplied"},
    ]
    assert build_event_risk_label("critical") == "CRITICAL"
    assert build_event_risk_label("critical", confidence="low") == "ELEVATED"
    assert build_event_time_window_filter(events, hours=24, now=datetime(2026, 6, 14, tzinfo=timezone.utc))["count"] == 2
    feed = build_intel_feed(events)
    assert feed["rows"][1]["status_label"] == "unconfirmed"
    assert feed["no_fake_live_data"] is True
    assert build_hotspot_panel(events)["rows"][0]["region"] == "Red Sea"
    assert build_locate_action_payload(events[0])["enabled"] is True
    presets = build_view_presets()["presets"]
    assert {"Global", "Crypto Stress", "Provider Gaps"} <= {p["name"] for p in presets}
    assert build_layer_panel_payload(["osint"])["enabled_count"] == 1
