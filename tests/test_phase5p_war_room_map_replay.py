from __future__ import annotations

import sqlite3

import pytest

from lib.research_workspace_migrations import get_workspace_schema_version
from lib.research_workspace_schema import SCHEMA_VERSION
from lib.war_room_map_replay import (
    build_demo_war_room_map_replay_contract,
    build_war_room_map_replay_contract,
    capture_war_room_map_snapshot,
    diff_war_room_map_snapshots,
    get_war_room_map_snapshot,
    list_war_room_map_snapshots,
    normalize_snapshot_id,
    prune_expired_war_room_map_snapshots,
)


def _payload(*, severity: str = "watch", include_second: bool = False) -> dict:
    markers = [
        {
            "marker_id": "marker:event-a",
            "event_id": "event-a",
            "title": "Observed event A",
            "summary": "Source-backed observation.",
            "lat": 37.5,
            "lon": 127.0,
            "coordinate_method": "provider_coordinates",
            "coordinate_status": "source-backed",
            "provider": "usgs",
            "source": "USGS",
            "source_url": "https://example.test/event-a",
            "fetched_at": "2026-06-22T01:00:00+00:00",
            "timestamp": "2026-06-22T00:55:00+00:00",
            "freshness": "live/fresh",
            "source_status": "live/fresh",
            "confidence": 0.9,
            "severity": severity,
            "region": "East Asia",
            "layer_ids": ["earthquakes"],
            "caveat": "Observed provider row.",
            "data_gap": "",
        }
    ]
    if include_second:
        markers.append(
            {
                **markers[0],
                "marker_id": "marker:event-b",
                "event_id": "event-b",
                "title": "Observed event B",
                "source_url": "https://example.test/event-b",
                "lat": 35.0,
            }
        )
    return {
        "data": {
            "markers": markers,
            "layer_health": [{"layer_id": "earthquakes", "label": "Earthquakes", "provider": "usgs", "source_status": "live/fresh", "availability": "available", "row_count": len(markers), "latest_fetched_at": "2026-06-22T01:00:00+00:00", "caveat": "USGS rows."}],
            "provider_health": [{"provider": "usgs", "status": "live/fresh", "availability": "available", "row_count": len(markers), "fetched_at": "2026-06-22T01:00:00+00:00", "caveat": "Public feed."}],
            "news_rows": [{"event_id": "event-a", "title": "Observed report", "provider": "rss", "source_url": "https://example.test/report", "published_at": "2026-06-22T00:58:00+00:00", "fetched_at": "2026-06-22T01:00:00+00:00", "source_status": "cached", "confidence": 0.7, "caveat": "Source report."}],
            "connected_assets": [{"id": "asset:SPY", "symbol": "SPY", "label": "SPY", "type": "etf", "provider": "taxonomy", "source_status": "inferred/proxy", "confidence": 0.4, "caveat": "Inferred context."}],
            "source_register": [{"provider": "usgs", "source": "USGS", "source_url": "https://example.test/event-a", "fetched_at": "2026-06-22T01:00:00+00:00", "source_status": "live/fresh", "confidence": 0.9, "coordinate_method": "provider_coordinates", "caveat": "Observed provider row.", "data_gap": ""}],
            "summary": {"source_status": "live/fresh"},
        }
    }


def test_schema_v6_adds_append_only_snapshot_table(tmp_path):
    db = tmp_path / "workspace.db"
    assert build_war_room_map_replay_contract(db_path=db)["historical_truth"] == "empty-local-store"
    assert get_workspace_schema_version(db) == SCHEMA_VERSION
    assert SCHEMA_VERSION >= 7
    with sqlite3.connect(db) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(war_room_map_snapshots)")}
    assert {"snapshot_id", "content_hash", "markers_json", "source_register_json", "retention_until"} <= columns


def test_capture_is_append_only_and_identical_content_is_deduplicated(tmp_path):
    db = tmp_path / "workspace.db"
    first = capture_war_room_map_snapshot(_payload(), runtime_mode="cache", captured_at="2026-06-22T01:05:00+00:00", db_path=db)
    duplicate = capture_war_room_map_snapshot(_payload(), runtime_mode="cache", captured_at="2026-06-22T02:05:00+00:00", db_path=db)
    changed = capture_war_room_map_snapshot(_payload(severity="elevated"), runtime_mode="cache", captured_at="2026-06-22T03:05:00+00:00", db_path=db)
    assert first["created"] is True and first["deduplicated"] is False
    assert duplicate["snapshot_id"] == first["snapshot_id"] and duplicate["deduplicated"] is True
    assert changed["snapshot_id"] != first["snapshot_id"]
    assert [row["snapshot_id"] for row in list_war_room_map_snapshots(db_path=db)] == [changed["snapshot_id"], first["snapshot_id"]]


def test_replay_diff_preserves_before_and_after_source_truth(tmp_path):
    db = tmp_path / "workspace.db"
    before = capture_war_room_map_snapshot(_payload(), captured_at="2026-06-22T01:05:00+00:00", db_path=db)
    after = capture_war_room_map_snapshot(_payload(severity="elevated", include_second=True), captured_at="2026-06-22T02:05:00+00:00", db_path=db)
    replay = build_war_room_map_replay_contract(snapshot_id=after["snapshot_id"], compare_to=before["snapshot_id"], db_path=db)
    event_diff = replay["diff"]["collections"]["events"]
    assert event_diff["summary"] == {"added": 1, "removed": 0, "changed": 1, "unchanged": 0, "refreshed": 0}
    changed = event_diff["changed"][0]
    assert changed["before"]["provider"] == changed["after"]["provider"] == "usgs"
    assert changed["before"]["source_url"] == "https://example.test/event-a"
    assert {"severity"} <= set(changed["changed_fields"])
    assert replay["historical_truth"] == "project-captured-observations-only"


def test_diff_reports_removed_rows_without_claiming_resolution():
    before = {"snapshot_id": "before", "markers": _payload(include_second=True)["data"]["markers"], "layers": [], "providers": [], "news": [], "assets": []}
    after = {"snapshot_id": "after", "markers": _payload()["data"]["markers"], "layers": [], "providers": [], "news": [], "assets": []}
    diff = diff_war_room_map_snapshots(before, after)
    assert diff["collections"]["events"]["summary"]["removed"] == 1
    assert "does not prove" in diff["caveat"]


def test_fetch_clock_only_updates_are_not_presented_as_material_changes():
    before_row = _payload()["data"]["markers"][0]
    after_row = {**before_row, "fetched_at": "2026-06-22T02:00:00+00:00"}
    before = {"snapshot_id": "before", "markers": [before_row], "layers": [], "providers": [], "news": [], "assets": []}
    after = {"snapshot_id": "after", "markers": [after_row], "layers": [], "providers": [], "news": [], "assets": []}
    events = diff_war_room_map_snapshots(before, after)["collections"]["events"]
    assert events["summary"]["changed"] == 0
    assert events["summary"]["refreshed"] == 1


def test_retention_is_explicit_and_snapshot_ids_are_bounded(tmp_path):
    db = tmp_path / "workspace.db"
    row = capture_war_room_map_snapshot(_payload(), captured_at="2026-01-01T00:00:00+00:00", retention_days=1, db_path=db)
    assert prune_expired_war_room_map_snapshots(as_of="2026-01-03T00:00:00+00:00", db_path=db) == 1
    with pytest.raises(KeyError):
        get_war_room_map_snapshot(row["snapshot_id"], db_path=db)
    for invalid in ["../workspace.db", "mapsnap_<script>", "", "mapsnap_123"]:
        with pytest.raises(ValueError):
            normalize_snapshot_id(invalid)


def test_snapshot_normalization_drops_private_and_unbounded_fields(tmp_path):
    db = tmp_path / "workspace.db"
    payload = _payload()
    payload["data"]["markers"][0]["api_key"] = "secret-value"
    payload["data"]["markers"][0]["raw_payload"] = {"secret": "raw"}
    payload["data"]["markers"][0]["summary"] = "x" * 5000
    row = capture_war_room_map_snapshot(payload, db_path=db)
    stored = get_war_room_map_snapshot(row["snapshot_id"], db_path=db)
    marker = stored["markers"][0]
    assert "api_key" not in marker and "raw_payload" not in marker
    assert len(marker["summary"]) == 1200


def test_demo_replay_is_explicitly_fictional_and_database_free():
    payload = build_demo_war_room_map_replay_contract()
    assert payload["historical_truth"] == "fictional-demo"
    assert payload["active_snapshot"]["source_status"] == "fixture"
    assert payload["readiness"]["capture_available"] is False
    assert payload["diff"]["summary"]["added"] == 1
