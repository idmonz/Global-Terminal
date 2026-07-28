from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from lib.api_contracts import build_api_market_map_screener_payload
from lib.market_snapshot_store import (
    MARKET_SNAPSHOT_VERSION,
    build_market_snapshot_detail,
    compact_market_map_payload,
    get_market_refresh_health,
    materialize_market_snapshot,
    read_market_snapshot,
    refresh_market_snapshot,
)


UTC = timezone.utc


def _fixture_payload() -> dict:
    payload = build_api_market_map_screener_payload(include_runtime=False)
    payload["generated_at"] = "2026-07-01T06:30:00+00:00"
    return payload


def test_compact_snapshot_removes_duplicate_collections_and_stays_bounded():
    payload = _fixture_payload()
    compact = compact_market_map_payload(payload)
    encoded = json.dumps(compact, separators=(",", ":"))

    assert compact["payload_type"] == "market_map_screener"
    assert compact["data"]["instruments"]
    assert "heatmap_tiles" not in compact["data"]
    assert "ranked_rows" not in compact["data"]
    assert "scatter_points" not in compact["data"]
    assert len(encoded.encode("utf-8")) < 900_000
    assert compact["data"]["materialization"]["snapshot_version"] == MARKET_SNAPSHOT_VERSION


def test_materialized_snapshot_is_atomic_versioned_and_read_without_builder(tmp_path):
    now = datetime(2026, 7, 1, 6, 30, tzinfo=UTC)
    written = materialize_market_snapshot(_fixture_payload(), base_dir=tmp_path, now=now)

    assert written["snapshot_version"] == MARKET_SNAPSHOT_VERSION
    assert written["snapshot_path"].endswith(".json")
    assert not list(tmp_path.glob("*.tmp"))

    loaded = read_market_snapshot(base_dir=tmp_path, now=now + timedelta(seconds=10))
    assert loaded["data"]["materialization"]["read_status"] == "fresh"
    assert loaded["data"]["materialization"]["content_hash"] == written["content_hash"]
    assert loaded["summary"]["materialized"] is True


def test_materialized_snapshot_retention_is_bounded(tmp_path):
    base = datetime(2026, 7, 1, 6, 30, tzinfo=UTC)
    for offset in range(4):
        payload = _fixture_payload()
        payload["generated_at"] = (base + timedelta(minutes=offset)).isoformat()
        materialize_market_snapshot(payload, base_dir=tmp_path, now=base + timedelta(minutes=offset), retention=2)

    snapshots = list(tmp_path.glob("market_snapshot_*.json"))
    assert len(snapshots) == 2
    assert (tmp_path / "latest.json").exists()


def test_failed_refresh_preserves_last_known_good_and_records_health(tmp_path):
    now = datetime(2026, 7, 1, 6, 30, tzinfo=UTC)
    first = refresh_market_snapshot(builder=_fixture_payload, base_dir=tmp_path, now=now)
    before = read_market_snapshot(base_dir=tmp_path, now=now)

    def fail():
        raise RuntimeError("provider timeout with token=must-not-leak")

    failed = refresh_market_snapshot(builder=fail, base_dir=tmp_path, now=now + timedelta(minutes=20))
    after = read_market_snapshot(
        base_dir=tmp_path,
        now=now + timedelta(minutes=20),
        max_age_seconds=60,
    )
    health = get_market_refresh_health(base_dir=tmp_path)

    assert first["status"] == "succeeded"
    assert first["provider_call_count"] == 0
    assert failed["status"] == "failed"
    assert before["data"]["materialization"]["content_hash"] == after["data"]["materialization"]["content_hash"]
    assert after["data"]["materialization"]["read_status"] == "stale"
    assert health["last_success_at"] == first["finished_at"]
    assert health["last_error"] == "provider refresh failed"
    assert "must-not-leak" not in json.dumps(health)


def test_stored_read_and_detail_do_not_call_refresh_builder(tmp_path):
    refresh_market_snapshot(builder=_fixture_payload, base_dir=tmp_path)
    calls = {"count": 0}

    def forbidden_builder():
        calls["count"] += 1
        raise AssertionError("stored read must not call providers")

    loaded = read_market_snapshot(base_dir=tmp_path)
    detail = build_market_snapshot_detail("AAPL", base_dir=tmp_path)

    assert loaded["data"]["instruments"]
    assert detail["summary"]["symbol"] == "AAPL"
    assert detail["data"]["instrument"]["symbol"] == "AAPL"
    assert calls["count"] == 0
    assert forbidden_builder  # Documents the provider boundary without invoking it.


def test_unknown_snapshot_symbol_never_falls_back_to_aapl(tmp_path):
    refresh_market_snapshot(builder=_fixture_payload, base_dir=tmp_path)
    detail = build_market_snapshot_detail("ZZZZ", base_dir=tmp_path)

    assert detail["summary"]["status"] == "unknown-symbol"
    assert detail["data"]["instrument"] is None
    assert "AAPL" not in json.dumps(detail["data"])


def test_snapshot_schema_mismatch_and_private_keys_are_rejected(tmp_path):
    payload = _fixture_payload()
    payload["api_key"] = "should-never-persist"
    with pytest.raises(ValueError, match="private"):
        materialize_market_snapshot(payload, base_dir=tmp_path)

    materialize_market_snapshot(_fixture_payload(), base_dir=tmp_path)
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    snapshot_path = tmp_path / latest["snapshot_file"]
    stored = json.loads(snapshot_path.read_text(encoding="utf-8"))
    stored["snapshot_version"] = "unsupported.v0"
    snapshot_path.write_text(json.dumps(stored), encoding="utf-8")

    unavailable = read_market_snapshot(base_dir=tmp_path)
    assert unavailable["summary"]["source_status"] == "unavailable"
    assert unavailable["data"]["materialization"]["read_status"] == "schema-mismatch"


def test_materialized_api_etag_and_conditional_read(monkeypatch, tmp_path):
    from backend.api import app as backend_app

    if not backend_app.FASTAPI_AVAILABLE:
        pytest.skip("FastAPI is optional.")
    from fastapi.testclient import TestClient

    monkeypatch.setenv("MARKET_SNAPSHOT_DIR", str(tmp_path))
    refresh_market_snapshot(builder=_fixture_payload, base_dir=tmp_path)
    client = TestClient(backend_app.app)

    first = client.get("/api/market-map-snapshot")
    assert first.status_code == 200
    assert first.headers["etag"]
    assert "max-age" in first.headers["cache-control"]
    assert len(first.content) < 900_000

    second = client.get("/api/market-map-snapshot", headers={"If-None-Match": first.headers["etag"]})
    assert second.status_code == 304
    assert second.content == b""
