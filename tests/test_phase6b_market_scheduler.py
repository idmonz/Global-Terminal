from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta

from lib.api_contracts import build_api_market_map_screener_payload
from lib.market_refresh_scheduler import run_market_refresh_schedule
from lib.market_snapshot_store import (
    get_market_refresh_history,
    read_market_snapshot,
    refresh_market_snapshot,
)


def _fixture():
    return build_api_market_map_screener_payload(include_runtime=False)


def test_refresh_history_is_bounded_append_only_and_secret_safe(tmp_path):
    base = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    for offset in range(4):
        refresh_market_snapshot(
            builder=_fixture,
            base_dir=tmp_path,
            now=base + timedelta(minutes=offset),
            history_retention=2,
        )

    history = get_market_refresh_history(base_dir=tmp_path, limit=10)
    encoded = json.dumps(history)

    assert history["history_version"] == "market_refresh_history.v1"
    assert len(history["rows"]) == 2
    assert history["rows"][0]["started_at"] > history["rows"][1]["started_at"]
    assert all(row["status"] == "succeeded" for row in history["rows"])
    assert all(row["instrument_count"] == 30 for row in history["rows"])
    assert all("taxonomy_coverage_count" in row for row in history["rows"])
    assert ".env" not in encoded
    assert "api_key" not in encoded.lower()


def test_failed_refresh_and_overlap_are_recorded_without_replacing_last_good(tmp_path):
    now = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    success = refresh_market_snapshot(builder=_fixture, base_dir=tmp_path, now=now)
    before = read_market_snapshot(base_dir=tmp_path, now=now)

    def fail():
        raise RuntimeError("provider failed with token=never-persist")

    failed = refresh_market_snapshot(
        builder=fail,
        base_dir=tmp_path,
        now=now + timedelta(minutes=1),
    )
    (tmp_path / ".refresh.lock").write_text("other-job", encoding="ascii")
    busy = refresh_market_snapshot(
        builder=_fixture,
        base_dir=tmp_path,
        now=now + timedelta(minutes=2),
    )
    (tmp_path / ".refresh.lock").unlink()
    after = read_market_snapshot(base_dir=tmp_path, now=now + timedelta(minutes=2))
    history = get_market_refresh_history(base_dir=tmp_path, limit=10)

    assert success["status"] == "succeeded"
    assert failed["status"] == "failed"
    assert busy["status"] == "single-flight-busy"
    assert before["data"]["instruments"] == after["data"]["instruments"]
    assert [row["status"] for row in history["rows"][:3]] == [
        "single-flight-busy",
        "failed",
        "succeeded",
    ]
    assert "never-persist" not in json.dumps(history)


def test_scheduler_supports_one_shot_bounded_loop_and_clean_stop():
    calls = []
    waits = []

    def refresh():
        calls.append(len(calls) + 1)
        return {"status": "succeeded", "job_id": f"job-{len(calls)}"}

    rows = run_market_refresh_schedule(
        refresh=refresh,
        interval_seconds=15,
        max_runs=3,
        wait=lambda seconds: waits.append(seconds) or False,
    )

    assert len(rows) == 3
    assert calls == [1, 2, 3]
    assert waits == [15, 15]

    stop = threading.Event()
    stop.set()
    stopped = run_market_refresh_schedule(
        refresh=refresh,
        interval_seconds=15,
        max_runs=None,
        stop_event=stop,
    )
    assert stopped == []


def test_refresh_history_api_is_bounded(monkeypatch, tmp_path):
    from backend.api import app as backend_app

    if not backend_app.FASTAPI_AVAILABLE:
        return
    from fastapi.testclient import TestClient

    monkeypatch.setenv("MARKET_SNAPSHOT_DIR", str(tmp_path))
    refresh_market_snapshot(builder=_fixture, base_dir=tmp_path)
    client = TestClient(backend_app.app)

    response = client.get("/api/market-refresh-history?limit=1")

    assert response.status_code == 200
    assert response.json()["history_version"] == "market_refresh_history.v1"
    assert len(response.json()["rows"]) == 1

