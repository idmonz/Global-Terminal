from __future__ import annotations

import json
import sqlite3

import pytest

from lib.api_contracts import build_api_daily_brief_payload, validate_api_payload
from lib.daily_briefing import (
    build_ai_safe_public_brief,
    build_current_daily_brief_contract,
    build_daily_brief_contract,
    build_daily_brief_history_contract,
    build_demo_daily_brief_contract,
    capture_daily_brief,
    diff_daily_briefs,
    get_daily_brief_capture,
    list_daily_brief_captures,
    normalize_brief_id,
    update_daily_brief_review,
    validate_ai_brief_draft,
)
from lib.research_workspace_migrations import get_workspace_schema_version
from lib.research_workspace_schema import SCHEMA_VERSION


def _inputs(*, market_change: float = 0.42, fetched_at: str = "2026-06-23T01:00:00+00:00") -> dict:
    source = {
        "provider": "official-market-test",
        "source": "Observed market test",
        "source_url": "https://example.test/market/SPY",
        "fetched_at": fetched_at,
        "observed_at": "2026-06-23T00:59:00+00:00",
        "freshness": "live/fresh",
        "source_status": "live/fresh",
        "confidence": 0.9,
        "caveat": "Test observation.",
        "data_gap": "No exchange entitlement in this test.",
    }
    return {
        "market": {
            "market_tape": [
                {
                    **source,
                    "symbol": "SPY",
                    "label": "S&P 500 ETF",
                    "asset_class": "etf",
                    "last_price": 550.0,
                    "daily_return_pct": market_change,
                    "one_month_return_pct": 1.8,
                }
            ]
        },
        "war_map": {
            "markers": [
                {
                    "marker_id": "event:test-one",
                    "title": "Observed logistics disruption",
                    "summary": "A provider recorded a logistics disruption.",
                    "region": "Red Sea",
                    "severity": "elevated",
                    "severity_score": 72,
                    "provider": "official-event-test",
                    "source": "Observed event test",
                    "source_url": "https://example.test/event/one",
                    "fetched_at": fetched_at,
                    "timestamp": "2026-06-23T00:50:00+00:00",
                    "freshness": "cached",
                    "source_status": "cached",
                    "confidence": 0.76,
                    "caveat": "Observed event, not a causal market explanation.",
                    "data_gap": "No live vessel positions.",
                    "related_asset_node_ids": ["commodity:brent-crude"],
                }
            ]
        },
        "news": {
            "normalized_news": [
                {
                    "title": "Public source reports a policy update",
                    "summary": "The report describes an observed policy update.",
                    "region": "Europe",
                    "provider": "public-rss-test",
                    "source": "Public RSS test",
                    "source_url": "https://example.test/news/policy",
                    "published_at": "2026-06-23T00:45:00+00:00",
                    "fetched_at": fetched_at,
                    "freshness": "live/fresh",
                    "source_status": "live/fresh",
                    "confidence": 0.72,
                    "caveat": "Headline-level source record.",
                    "data_gap": "Primary document not attached.",
                    "related_assets": ["EURUSD"],
                }
            ]
        },
        "provider_rows": [
            {
                "provider": "opensky",
                "source": "OpenSky OAuth",
                "source_status": "missing-key",
                "status": "missing-key",
                "availability": "unavailable",
                "fetched_at": None,
                "confidence": 0.0,
                "caveat": "Flight layer is not claimed live.",
                "data_gap": "OAuth credentials or a successful public request are unavailable.",
            }
        ],
        "watchlists": [
            {
                "symbol": "AAPL",
                "item_type": "equity",
                "watch_reason": "private unreleased thesis",
                "privacy_scope": "local-private",
            }
        ],
    }


def _brief(**changes) -> dict:
    inputs = _inputs(**changes)
    return build_daily_brief_contract(
        **inputs,
        period="morning",
        runtime_mode="live-if-available",
        generated_at="2026-06-23T01:05:00+00:00",
    )


def test_claim_ledger_precedes_narrative_and_every_material_sentence_is_source_bound():
    brief = _brief()
    source_ids = {row["source_id"] for row in brief["source_register"]}
    claim_ids = {row["claim_id"] for row in brief["claims"]}
    assert brief["daily_brief_version"] == "daily_brief.v1"
    assert brief["claims"] and brief["sections"]
    assert all(set(row["source_ids"]) <= source_ids for row in brief["claims"])
    assert all(row["source_ids"] for row in brief["claims"] if row["claim_kind"] != "gap")
    assert all(set(row["claim_ids"]) <= claim_ids for row in brief["sections"])
    assert all(row["not_financial_advice"] is True for row in brief["claims"])
    assert not brief["validation"]["issues"]


def test_provider_failure_becomes_a_gap_claim_instead_of_fake_live_coverage():
    brief = _brief()
    gap = next(row for row in brief["claims"] if row["claim_kind"] == "gap" and "opensky" in row["statement"].lower())
    assert gap["source_status"] == "missing-key"
    assert gap["data_gap"]
    assert brief["coverage"]["gap_count"] >= 1


def test_prior_comparison_separates_fetch_clock_refresh_from_material_change():
    before = _brief(market_change=0.42, fetched_at="2026-06-23T01:00:00+00:00")
    refreshed = _brief(market_change=0.42, fetched_at="2026-06-23T02:00:00+00:00")
    changed = _brief(market_change=-1.25, fetched_at="2026-06-23T02:00:00+00:00")
    refresh_diff = diff_daily_briefs(before, refreshed)
    changed_diff = diff_daily_briefs(before, changed)
    assert refresh_diff["summary"]["changed"] == 0
    assert refresh_diff["summary"]["refreshed"] >= 1
    assert changed_diff["summary"]["changed"] >= 1
    assert any("statement" in row["changed_fields"] for row in changed_diff["changed"])
    assert "does not establish causality" in changed_diff["caveat"]


def test_schema_v7_capture_is_append_only_deduplicated_and_reviewable(tmp_path):
    db = tmp_path / "briefs.db"
    first = capture_daily_brief(_brief(), db_path=db, captured_at="2026-06-23T01:06:00+00:00")
    duplicate = capture_daily_brief(
        _brief(fetched_at="2026-06-23T02:00:00+00:00"),
        db_path=db,
        captured_at="2026-06-23T02:06:00+00:00",
    )
    changed = capture_daily_brief(
        _brief(market_change=-1.25, fetched_at="2026-06-23T03:00:00+00:00"),
        db_path=db,
        captured_at="2026-06-23T03:06:00+00:00",
    )
    assert get_workspace_schema_version(db) == SCHEMA_VERSION
    assert SCHEMA_VERSION >= 7
    with sqlite3.connect(db) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(daily_brief_captures)")}
    assert {"brief_id", "content_hash", "claims_json", "source_register_json", "review_status", "retention_until"} <= columns
    assert first["created"] is True
    assert duplicate["deduplicated"] is True and duplicate["brief_id"] == first["brief_id"]
    assert changed["brief_id"] != first["brief_id"]
    assert len(list_daily_brief_captures(db_path=db)) == 2
    reviewed = update_daily_brief_review(changed["brief_id"], status="reviewed", review_notes="Local note", db_path=db)
    assert reviewed["review_status"] == "reviewed"
    assert reviewed["reviewed_at"]
    assert "review_notes" not in get_daily_brief_capture(changed["brief_id"], db_path=db)


def test_local_first_run_is_empty_and_demo_is_separate_fictional_history(tmp_path):
    local = build_daily_brief_history_contract(db_path=tmp_path / "empty.db")
    demo = build_demo_daily_brief_contract()
    assert local["historical_truth"] == "empty-local-store"
    assert local["captures"] == []
    assert demo["privacy_scope"] == "deterministic-public-fixture"
    assert demo["historical_truth"] == "fictional-demo"
    assert demo["comparison"]["summary"]["added"] + demo["comparison"]["summary"]["changed"] >= 1


def test_ai_boundary_excludes_private_watchlist_context_and_rejects_unsupported_drafts():
    brief = _brief()
    safe = build_ai_safe_public_brief(brief)
    encoded = json.dumps(safe)
    assert "private unreleased thesis" not in encoded
    assert "AAPL" not in encoded
    assert all(row["privacy_scope"] == "public" for row in safe["claims"])
    valid_claim = safe["claims"][0]["claim_id"]
    assert validate_ai_brief_draft({"paragraphs": [{"text": "Observed context only.", "claim_ids": [valid_claim]}]}, brief)["valid"] is True
    invalid = validate_ai_brief_draft({"paragraphs": [{"text": "Buy now at the target price.", "claim_ids": ["claim_missing"]}]}, brief)
    assert invalid["valid"] is False
    assert invalid["issues"]


def test_brief_ids_and_review_values_are_bounded(tmp_path):
    row = capture_daily_brief(_brief(), db_path=tmp_path / "bounded.db")
    assert normalize_brief_id(row["brief_id"]) == row["brief_id"]
    for invalid in ["../private.db", "brief_<script>", "", "brief_123"]:
        with pytest.raises(ValueError):
            normalize_brief_id(invalid)
    with pytest.raises(ValueError):
        update_daily_brief_review(row["brief_id"], status="approved-for-trade", db_path=tmp_path / "bounded.db")


def test_daily_brief_api_envelope_is_json_safe_and_claim_validated():
    envelope = build_api_daily_brief_payload(brief=_brief())
    valid, issues = validate_api_payload(envelope)
    assert valid, issues
    assert envelope["payload_type"] == "daily_brief"
    assert envelope["data"]["claims"]
    encoded = json.dumps(envelope)
    assert "private unreleased thesis" not in encoded
    assert "api_key" not in encoded.lower()


def test_current_brief_surfaces_optional_provider_gaps(monkeypatch, tmp_path):
    import lib.live_feeds as live_feeds

    monkeypatch.setattr(live_feeds, "fetch_opensky_optional_status", lambda: {
        "provider": "opensky",
        "source": "OpenSky optional flight layer",
        "status": "configured",
        "configured": True,
        "available": True,
        "caveat": "Flight rows are not claimed live until the provider succeeds.",
    })
    monkeypatch.setattr(live_feeds, "fetch_aisstream_optional_status", lambda: {
        "provider": "aisstream",
        "source": "AISStream optional vessel layer",
        "status": "configured",
        "configured": True,
        "available": True,
        "caveat": "Vessel rows are not claimed live until the provider succeeds.",
    })

    brief = build_current_daily_brief_contract(period="morning", include_runtime=False, db_path=tmp_path / "current.db")
    gap_statements = [row["statement"].lower() for row in brief["claims"] if row["claim_kind"] == "gap"]
    assert any("opensky coverage is configured-unverified" in statement for statement in gap_statements)
    assert any("aisstream coverage is configured-unverified" in statement for statement in gap_statements)
    assert brief["coverage"]["gap_count"] >= 2


def test_fastapi_daily_brief_capture_list_and_review_workflow(tmp_path, monkeypatch):
    try:
        from fastapi.testclient import TestClient
        from backend.api import app as backend_app
    except Exception as exc:  # pragma: no cover - optional dependency stack
        pytest.skip(str(exc))
    monkeypatch.setenv("RESEARCH_WORKSPACE_DB_PATH", str(tmp_path / "api-brief.db"))
    client = TestClient(backend_app.app)
    current = client.get("/api/daily-brief?mode=fixture&period=morning")
    assert current.status_code == 200
    assert current.json()["payload_type"] == "daily_brief"
    captured = client.post("/api/daily-brief/captures", json={"mode": "fixture", "period": "morning"})
    assert captured.status_code == 200
    brief_id = captured.json()["capture"]["brief_id"]
    listed = client.get("/api/daily-brief/captures")
    assert listed.status_code == 200 and listed.json()["captures"][0]["brief_id"] == brief_id
    reviewed = client.patch(f"/api/daily-brief/captures/{brief_id}/review", json={"status": "reviewed", "review_notes": "private local review"})
    assert reviewed.status_code == 200
    assert reviewed.json()["capture"]["review_status"] == "reviewed"
    assert "private local review" not in json.dumps(reviewed.json())


@pytest.mark.parametrize(
    "origin",
    ["http://127.0.0.1:3038", "http://127.0.0.1:3167", "http://localhost:3999"],
)
def test_daily_brief_cors_allows_localhost_product_ports(origin):
    try:
        from fastapi.testclient import TestClient
        from backend.api import app as backend_app
    except Exception as exc:  # pragma: no cover - optional dependency stack
        pytest.skip(str(exc))
    client = TestClient(backend_app.app)
    response = client.options(
        "/api/daily-brief/captures",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_daily_brief_cors_rejects_nonlocal_product_origin():
    try:
        from fastapi.testclient import TestClient
        from backend.api import app as backend_app
    except Exception as exc:  # pragma: no cover - optional dependency stack
        pytest.skip(str(exc))
    client = TestClient(backend_app.app)
    response = client.options(
        "/api/daily-brief/captures",
        headers={
            "Origin": "https://example.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
