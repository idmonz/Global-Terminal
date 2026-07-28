from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lib.research_workspace_db import execute_query, json_dumps


NOW = datetime(2026, 7, 3, 8, 30, tzinfo=timezone.utc)
PRIVATE_REASON = "phase6g-private-reason-must-not-leak"


def _source(status: str, fetched_at: str) -> dict:
    return {
        "provider": "test-provider",
        "source": "test-snapshot",
        "source_url": "https://example.com/source",
        "source_status": status,
        "freshness": status,
        "fetched_at": fetched_at,
        "confidence": 0.9,
        "caveat": "Test evidence only.",
        "data_gap": None,
    }


def _row(
    symbol: str,
    *,
    price: float,
    source_status: str = "cached",
    market_cap: float | None = 100_000_000_000,
    eps: float | None = None,
    event_date: str = "2026-07-30",
    news: list[dict] | None = None,
    fetched_at: str = "2026-07-03T07:00:00+00:00",
) -> dict:
    source = _source(source_status, fetched_at)
    return {
        "symbol": symbol,
        "status": "fresh" if source_status != "stale" else "stale",
        "source_status": source_status,
        "fetched_at": fetched_at,
        "quote": {
            "last_price": price,
            "change_pct": 1.2,
            "provider": source["provider"],
            "source_url": source["source_url"],
            "source_status": source_status,
            "retrieved_at": fetched_at,
        },
        "performance": {"return_1w_pct": 2.0, "return_1m_pct": 4.0},
        "financials": {
            "metrics": {"market_cap": market_cap, "eps": eps},
            "provider": source["provider"],
            "source_url": source["source_url"],
            "source_status": source_status,
            "fetched_at": fetched_at,
        },
        "catalysts": {
            "availability": "available",
            "source_status": source_status,
            "fetched_at": fetched_at,
            "earnings": [
                {
                    "event_type": "scheduled-earnings",
                    "event_date": event_date,
                    "provider": source["provider"],
                    "source_url": source["source_url"],
                    "source_status": source_status,
                    "fetched_at": fetched_at,
                }
            ],
            "dividends": [],
            "news": news or [],
        },
        "source_register": [source],
        "research_snapshot_version": "research_snapshot.v1",
    }


def _job(
    job_id: str,
    list_id: str,
    rows: list[dict],
    *,
    status: str = "completed",
    started_at: str,
    actual_calls: int = 1,
) -> dict:
    return {
        "job_id": job_id,
        "list_id": list_id,
        "status": status,
        "requested_count": len(rows),
        "completed_count": len(rows) if status == "completed" else 0,
        "failed_count": 0 if status == "completed" else len(rows),
        "skipped_count": 0,
        "provider_call_budget": 16,
        "provider_call_count": actual_calls,
        "queue_depth": len(rows),
        "duration_ms": 1200,
        "interval": "1d",
        "range": "3mo",
        "started_at": started_at,
        "completed_at": started_at,
        "last_error": None if status == "completed" else "provider unavailable",
        "rows": rows,
        "provider_budget": {
            "maximum_calls": 16,
            "actual_calls": actual_calls,
            "cache_hits": 15 if actual_calls == 1 else 0,
            "stale_hits": 0,
            "failed_calls": 0 if status == "completed" else 1,
            "blocked_calls": 0,
            "skipped_calls": 0,
            "next_safe_refresh_at": "2026-07-03T09:00:00+00:00",
        },
    }


def _insert_job(db: Path, job: dict) -> None:
    execute_query(
        """
        INSERT INTO watchlist_materialization_jobs (
            job_id, list_id, status, requested_count, completed_count, failed_count,
            skipped_count, provider_call_budget, provider_call_count, queue_depth,
            duration_ms, interval, range_name, started_at, completed_at, last_error,
            rows_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job["job_id"],
            job["list_id"],
            job["status"],
            job["requested_count"],
            job["completed_count"],
            job["failed_count"],
            job["skipped_count"],
            job["provider_call_budget"],
            job["provider_call_count"],
            job["queue_depth"],
            job["duration_ms"],
            job["interval"],
            job["range"],
            job["started_at"],
            job["completed_at"],
            job.get("last_error") or "",
            json_dumps({"rows": job["rows"], "provider_budget": job["provider_budget"]}),
            job["started_at"],
        ),
        db_path=db,
    )


def test_snapshot_diff_is_deterministic_source_preserving_and_null_safe():
    from lib.research_snapshot_diff import build_research_snapshot_diff

    previous = _job(
        "job_previous",
        "daily",
        [_row("AAPL", price=100, eps=None, event_date="2026-07-30")],
        started_at="2026-07-03T06:00:00+00:00",
    )
    current = _job(
        "job_current",
        "daily",
        [
            _row(
                "AAPL",
                price=102,
                eps=0,
                event_date="2026-08-01",
                source_status="stale",
                news=[
                    {
                        "title": "AAPL exact company update",
                        "published_at": "2026-07-03T07:15:00+00:00",
                        "source_url": "https://example.com/aapl-update",
                        "provider": "test-provider",
                        "source_status": "cached",
                        "exact_symbol_scope": True,
                    }
                ],
            )
        ],
        started_at="2026-07-03T08:00:00+00:00",
    )

    first = build_research_snapshot_diff(previous, current, now=NOW)
    second = build_research_snapshot_diff(previous, current, now=NOW)
    assert first == second
    assert first["diff_version"] == "research_snapshot_diff.v1"
    assert first["provider_call_count"] == 0
    assert first["comparison_status"] == "ready"
    assert {"price", "event", "news", "source-status"} <= {
        row["change_type"] for row in first["changes"]
    }
    assert not any(
        row["change_type"] == "fundamental" and row["field"] == "eps"
        for row in first["changes"]
    )
    assert all(row["change_id"].startswith("change_") for row in first["changes"])
    assert all("evidence" in row and "observation" in row for row in first["changes"])
    assert any(row["transition"] == "degraded" for row in first["changes"])


def test_snapshot_diff_rejects_cross_list_and_handles_added_removed_symbols():
    from lib.research_snapshot_diff import build_research_snapshot_diff

    previous = _job(
        "job_previous",
        "first",
        [_row("AAPL", price=100), _row("JNJ", price=200)],
        started_at="2026-07-03T06:00:00+00:00",
    )
    current = _job(
        "job_current",
        "first",
        [_row("AAPL", price=100), _row("TSLA", price=300)],
        started_at="2026-07-03T08:00:00+00:00",
    )
    result = build_research_snapshot_diff(previous, current, now=NOW)
    symbol_changes = {(row["symbol"], row["transition"]) for row in result["changes"] if row["change_type"] == "symbol"}
    assert symbol_changes == {("JNJ", "removed"), ("TSLA", "added")}

    with pytest.raises(ValueError, match="same watchlist"):
        build_research_snapshot_diff(previous, {**current, "list_id": "second"}, now=NOW)


def test_refresh_operations_separates_latest_attempt_success_and_kill_switch():
    from lib.research_snapshot_diff import build_refresh_operations_contract

    older = _job(
        "job_old",
        "daily",
        [_row("AAPL", price=100)],
        started_at="2026-07-03T06:00:00+00:00",
    )
    latest_success = _job(
        "job_success",
        "daily",
        [_row("AAPL", price=102)],
        started_at="2026-07-03T07:00:00+00:00",
    )
    failed = _job(
        "job_failed",
        "daily",
        [],
        status="failed",
        started_at="2026-07-03T08:00:00+00:00",
        actual_calls=0,
    )
    operations = build_refresh_operations_contract(
        [failed, latest_success, older],
        now=NOW,
        background_enabled=False,
        busy=False,
    )
    assert operations["last_attempt"]["job_id"] == "job_failed"
    assert operations["last_success"]["job_id"] == "job_success"
    assert operations["previous_success"]["job_id"] == "job_old"
    assert operations["installed_background_service"] is False
    assert operations["background"]["kill_switch_engaged"] is True
    assert operations["manual_refresh"]["available"] is True
    assert operations["budget"]["maximum_calls"] == 16
    assert operations["bounded_event_history"][0]["job_id"] == "job_failed"


def test_change_alert_preview_requires_opt_in_and_honors_dedupe_cooldown_expiry_ack(tmp_path):
    from lib.research_snapshot_diff import (
        acknowledge_change_alert_event,
        build_change_alert_preview,
        persist_change_alert_previews,
        upsert_watchlist_change_rule,
    )

    db = tmp_path / "alerts.db"
    previous = _job(
        "job_previous",
        "daily",
        [_row("AAPL", price=100)],
        started_at="2026-07-03T06:00:00+00:00",
    )
    current = _job(
        "job_current",
        "daily",
        [_row("AAPL", price=104)],
        started_at="2026-07-03T08:00:00+00:00",
    )
    from lib.research_snapshot_diff import build_research_snapshot_diff

    diff = build_research_snapshot_diff(previous, current, now=NOW)
    disabled = build_change_alert_preview(diff, rule=None, events=[], now=NOW)
    assert disabled["opt_in"] is False
    assert disabled["delivery"] == "preview-only"

    rule = upsert_watchlist_change_rule(
        "daily",
        enabled=True,
        minimum_severity="material",
        cooldown_minutes=60,
        db_path=db,
    )
    first = persist_change_alert_previews("daily", diff, db_path=db, now=NOW)
    second = persist_change_alert_previews("daily", diff, db_path=db, now=NOW)
    assert rule["scope"] == "watchlist_change"
    assert first["stored_count"] >= 1
    assert second["stored_count"] == 0
    assert second["duplicate_count"] >= 1

    event_id = first["events"][0]["event_id"]
    acknowledged = acknowledge_change_alert_event(event_id, db_path=db, now=NOW)
    assert acknowledged["acknowledgement_status"] == "acknowledged"
    assert acknowledged["acknowledged_at"] == NOW.isoformat()

    cooldown_rule = {**rule, "last_triggered_at": "2026-07-03T08:10:00+00:00"}
    cooldown = build_change_alert_preview(diff, rule=cooldown_rule, events=[], now=NOW)
    assert cooldown["status"] == "cooldown"
    expired_rule = {**rule, "expires_at": "2026-07-03T08:00:00+00:00"}
    expired = build_change_alert_preview(diff, rule=expired_rule, events=[], now=NOW)
    assert expired["status"] == "expired"


def test_watchlist_contract_uses_two_successes_and_retains_failed_attempt(tmp_path):
    from lib.watchlist_desk import (
        add_watchlist_symbol,
        build_watchlist_desk_contract,
        create_watchlist,
    )

    db = tmp_path / "phase6g.db"
    create_watchlist("Daily", list_id="daily", db_path=db)
    add_watchlist_symbol(
        "daily",
        "AAPL",
        asset_class="equity",
        private_reason=PRIVATE_REASON,
        db_path=db,
    )
    _insert_job(
        db,
        _job("old", "daily", [_row("AAPL", price=100)], started_at="2026-07-03T06:00:00+00:00"),
    )
    _insert_job(
        db,
        _job("current", "daily", [_row("AAPL", price=103)], started_at="2026-07-03T07:00:00+00:00"),
    )
    _insert_job(
        db,
        _job("failed", "daily", [], status="failed", started_at="2026-07-03T08:00:00+00:00", actual_calls=0),
    )
    contract = build_watchlist_desk_contract(list_id="daily", selected_symbol="AAPL", db_path=db)
    encoded = json.dumps(contract)

    assert contract["change_inbox"]["comparison_status"] == "ready"
    assert contract["change_inbox"]["current_snapshot_id"] == "current"
    assert contract["refresh_operations"]["last_attempt"]["job_id"] == "failed"
    assert contract["refresh_operations"]["last_success"]["job_id"] == "current"
    assert contract["alert_readiness"]["delivery"] == "preview-only"
    assert PRIVATE_REASON not in encoded


def test_phase6g_http_diff_is_etagged_private_and_unknown_list_isolated(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api.app import create_app
    from lib.watchlist_desk import add_watchlist_symbol, create_watchlist

    db = tmp_path / "phase6g-api.db"
    monkeypatch.setenv("RESEARCH_WORKSPACE_DB_PATH", str(db))
    create_watchlist("Daily", list_id="daily", db_path=db)
    add_watchlist_symbol("daily", "AAPL", asset_class="equity", private_reason=PRIVATE_REASON, db_path=db)
    _insert_job(
        db,
        _job("old", "daily", [_row("AAPL", price=100)], started_at="2026-07-03T06:00:00+00:00"),
    )
    _insert_job(
        db,
        _job("current", "daily", [_row("AAPL", price=103)], started_at="2026-07-03T07:00:00+00:00"),
    )
    client = TestClient(create_app())
    response = client.get("/api/watchlist-desk/lists/daily/changes")
    assert response.status_code == 200
    assert response.headers["etag"]
    assert PRIVATE_REASON not in response.text
    conditional = client.get(
        "/api/watchlist-desk/lists/daily/changes",
        headers={"If-None-Match": response.headers["etag"]},
    )
    assert conditional.status_code == 304
    missing = client.get("/api/watchlist-desk/lists/missing/changes")
    assert missing.status_code == 404
    assert "AAPL" not in missing.text


def test_phase6g_frontend_exposes_change_inbox_filters_preview_and_return_state():
    root = Path(__file__).resolve().parents[1]
    watchlist = (root / "apps/web/src/components/WatchlistDesk.tsx").read_text(encoding="utf-8")
    routes = (root / "apps/web/src/lib/product-routes.ts").read_text(encoding="utf-8")
    visual = (root / "apps/web/scripts/capture-phase6g.mjs").read_text(encoding="utf-8")

    assert 'key: "changes"' in watchlist
    assert "data-watchlist-change-count" in watchlist
    assert 'next.searchParams.set("changeType"' in watchlist
    assert 'next.searchParams.set("changeSeverity"' in watchlist
    assert 'next.searchParams.set("change"' in watchlist
    assert "Preview only" in watchlist
    assert '"changes"' in routes
    assert "changeType" in routes and "changeSeverity" in routes
    assert "data-provider-fanout" in visual
    assert "providerRequests === 0" in visual


def test_phase6g_fixture_does_not_duplicate_snapshot_rows_in_job_metadata():
    from lib.watchlist_desk import build_watchlist_desk_fixture_contract

    contract = build_watchlist_desk_fixture_contract()
    materialization = contract["materialization"]
    assert "rows" not in materialization["latest_job"]
    assert "rows" not in materialization["latest_success"]
    assert len(json.dumps(contract, separators=(",", ":")).encode("utf-8")) < 100_000
