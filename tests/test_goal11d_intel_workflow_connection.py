from datetime import datetime, timezone

from lib.intel_event_actions import run_intel_event_action
from lib.intel_feed_workflow import build_intel_workflow_payload
from lib.view_preset_filters import filter_events_by_preset, filter_events_by_time_window
from lib.watchlist_store import list_watchlist_items


def _events():
    return [
        {"event_id": "e1", "title": "Red Sea shipping disruption", "region": "Red Sea", "severity": "high", "confidence": "high", "created_at": "2026-06-14T00:00:00+00:00", "lat": 1, "lon": 2},
        {"event_id": "e2", "title": "Hormuz tanker risk", "region": "Hormuz / Persian Gulf", "severity": "critical", "confidence": "low", "created_at": "2026-06-13T18:00:00+00:00", "location_inferred": True},
        {"event_id": "e3", "title": "Old Europe event", "region": "Europe", "severity": "low", "confidence": "high", "created_at": "2026-06-01T00:00:00+00:00"},
    ]


def test_goal11d_presets_time_windows_locate_and_low_confidence():
    now = datetime(2026, 6, 14, 1, tzinfo=timezone.utc)
    red = build_intel_workflow_payload(_events(), preset="Red Sea / Suez", hours=24, now=now)
    assert len(red["events"]) == 1
    assert red["events"][0]["region"] == "Red Sea"
    assert red["feed"]["rows"][0]["locate_action"]["target_page"] == "pages/14_War_Room.py"
    assert red["layers"]["enabled_count"] >= 1

    hormuz = build_intel_workflow_payload(_events(), preset="Hormuz / Persian Gulf", hours=24, now=now)
    assert len(hormuz["events"]) == 1
    assert hormuz["feed"]["rows"][0]["status_label"] == "unconfirmed"
    assert hormuz["feed"]["rows"][0]["location_label"] == "inferred"
    assert filter_events_by_time_window(_events(), hours=6, now=now)[0]["event_id"] == "e1"


def test_goal11d_intel_event_add_region_to_watchlist(tmp_path):
    db = tmp_path / "workspace.db"
    event = _events()[0]
    result = run_intel_event_action(event, "ADD_WATCHLIST_ITEM", db_path=db)
    assert result["ok"] is True
    assert list_watchlist_items(db_path=db)[0]["region"] == "Red Sea"
