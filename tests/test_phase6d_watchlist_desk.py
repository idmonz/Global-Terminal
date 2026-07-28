from __future__ import annotations

import json

import pytest

from lib.api_contracts import validate_api_payload
from lib.symbol_intelligence import build_symbol_delivery_contract
from lib.watchlist_desk import (
    WatchlistConflict,
    add_watchlist_symbol,
    build_watchlist_desk_contract,
    create_watchlist,
    materialize_watchlist,
    rename_watchlist,
    reorder_watchlist,
)


PRIVATE_REASON = "phase6d-private-thesis-must-not-leak"


def test_named_watchlist_crud_order_and_public_privacy(tmp_path):
    db = tmp_path / "watchlists.db"
    created = create_watchlist("Daily Radar", list_id="daily-radar", db_path=db)
    assert created["list_id"] == "daily-radar"

    first = add_watchlist_symbol(
        "daily-radar",
        "AAPL",
        asset_class="equity",
        private_reason=PRIVATE_REASON,
        db_path=db,
    )
    second = add_watchlist_symbol(
        "daily-radar",
        "MSFT",
        asset_class="equity",
        private_reason="second private note",
        db_path=db,
    )
    assert first["symbol"] == "AAPL"
    assert "watch_reason" not in first

    with pytest.raises(WatchlistConflict):
        add_watchlist_symbol("daily-radar", "AAPL", asset_class="equity", db_path=db)

    reordered = reorder_watchlist(
        "daily-radar",
        [second["item_id"], first["item_id"]],
        db_path=db,
    )
    assert [row["symbol"] for row in reordered] == ["MSFT", "AAPL"]
    assert rename_watchlist("daily-radar", "Opening Bell", db_path=db)["name"] == "Opening Bell"

    contract = build_watchlist_desk_contract(
        list_id="daily-radar",
        selected_symbol="MSFT",
        db_path=db,
    )
    encoded = json.dumps(contract)
    assert PRIVATE_REASON not in encoded
    assert "second private note" not in encoded
    assert "watch_reason" not in encoded
    assert contract["selected"]["symbol"] == "MSFT"
    assert contract["privacy"]["scope"] == "local-private"


def test_watchlist_rejects_unknown_and_asset_class_mismatch(tmp_path):
    db = tmp_path / "watchlists.db"
    create_watchlist("Exact", list_id="exact", db_path=db)

    with pytest.raises(ValueError, match="unknown-symbol"):
        add_watchlist_symbol("exact", "NOTAREAL123", asset_class="equity", db_path=db)
    with pytest.raises(ValueError, match="asset-class-mismatch"):
        add_watchlist_symbol("exact", "AAPL", asset_class="crypto", db_path=db)

    assert build_watchlist_desk_contract(list_id="exact", db_path=db)["items"] == []


def test_materialization_is_bounded_and_records_health(tmp_path, monkeypatch):
    import lib.watchlist_desk as desk

    db = tmp_path / "watchlists.db"
    create_watchlist("Bounded", list_id="bounded", db_path=db)
    for symbol in ["AAPL", "MSFT", "NVDA", "AMZN", "META"]:
        add_watchlist_symbol("bounded", symbol, asset_class="equity", db_path=db)

    calls: list[list[str]] = []

    def fake_prime(identities, *, interval, range_name):
        calls.append([row["symbol"] for row in identities])
        return {
            "rows": [
                {
                    "symbol": row["symbol"],
                    "status": "fresh",
                    "source_status": "live/fresh",
                    "history_row_count": 62,
                    "fetched_at": "2026-07-02T00:00:00+00:00",
                    "data_gap": None,
                }
                for row in identities
            ],
            "provider_call_count": 1,
        }

    monkeypatch.setattr(desk, "_prime_history_batch", fake_prime)
    result = materialize_watchlist(
        "bounded",
        interval="1d",
        range_name="3mo",
        max_symbols=3,
        db_path=db,
    )

    assert calls == [["AAPL", "MSFT", "NVDA"]]
    assert result["status"] == "completed"
    assert result["requested_count"] == 3
    assert result["skipped_count"] == 2
    assert result["provider_call_count"] == 1
    assert result["provider_call_budget"] == 3
    assert result["broad_universe_rebuild"] is False
    assert result["queue_depth"] == 3

    contract = build_watchlist_desk_contract(list_id="bounded", db_path=db)
    assert contract["materialization"]["latest_job"]["job_id"] == result["job_id"]
    assert contract["materialization"]["latest_job"]["status"] == "completed"


def test_materialization_overlap_is_busy_without_provider_call(tmp_path, monkeypatch):
    import lib.watchlist_desk as desk

    db = tmp_path / "watchlists.db"
    create_watchlist("Busy", list_id="busy", db_path=db)
    add_watchlist_symbol("busy", "AAPL", asset_class="equity", db_path=db)
    key = desk.materialization_lock_key("busy", db_path=db)
    desk._ACTIVE_MATERIALIZATIONS.add(key)
    monkeypatch.setattr(
        desk,
        "_prime_history_batch",
        lambda *args, **kwargs: pytest.fail("provider work must not run"),
    )
    try:
        result = materialize_watchlist("busy", db_path=db)
    finally:
        desk._ACTIVE_MATERIALIZATIONS.discard(key)

    assert result["status"] == "busy"
    assert result["provider_call_count"] == 0
    assert result["last_error"] == "another materialization is active"


def test_summary_delivery_does_not_load_financial_or_news(monkeypatch):
    import lib.symbol_intelligence as intelligence

    monkeypatch.setattr(
        intelligence,
        "_financial_context",
        lambda *args, **kwargs: pytest.fail("summary must not load financials"),
    )
    monkeypatch.setattr(
        intelligence,
        "_exact_news",
        lambda *args, **kwargs: pytest.fail("summary must not load news"),
    )
    payload = build_symbol_delivery_contract(
        "AAPL",
        asset_class="equity",
        runtime_mode="fixture",
        delivery="summary",
    )
    workstation = payload["workstations"][0]

    assert payload["delivery"]["loaded_panels"] == ["summary"]
    assert workstation["identity"]["symbol"] == "AAPL"
    assert workstation["financial_context"]["availability"] == "not-loaded"
    assert workstation["exact_news"]["availability"] == "not-loaded"
    assert workstation["history"] == []
    assert len(json.dumps(payload)) < 50_000


def test_chart_and_detail_delivery_are_exact_and_panel_scoped(monkeypatch):
    import lib.symbol_intelligence as intelligence

    financial_calls: list[str] = []
    news_calls: list[str] = []

    def fake_financial(identity, *args, **kwargs):
        financial_calls.append(identity["symbol"])
        return {
            "availability": "available",
            "source_status": "cached",
            "provider": "test-financial",
            "fetched_at": "2026-07-02T00:00:00+00:00",
            "metrics": {"market_cap": 1.0},
            "statements": {},
            "sec_facts": {"facts": [], "source_register": []},
            "earnings_calendar": {"rows": [], "source_register": []},
            "source_register": [],
            "caveat": "test",
            "data_gap": None,
        }

    def fake_news(identity, *args, **kwargs):
        news_calls.append(identity["symbol"])
        return {
            "availability": "available",
            "source_status": "cached",
            "provider": "test-news",
            "fetched_at": "2026-07-02T00:00:00+00:00",
            "rows": [],
            "source_register": [],
            "caveat": "test",
            "data_gap": None,
        }

    monkeypatch.setattr(intelligence, "_financial_context", fake_financial)
    monkeypatch.setattr(intelligence, "_exact_news", fake_news)

    chart = build_symbol_delivery_contract(
        "AAPL",
        asset_class="equity",
        runtime_mode="fixture",
        delivery="chart",
    )
    assert chart["workstations"][0]["history"]
    assert financial_calls == []
    assert news_calls == []

    financial = build_symbol_delivery_contract(
        "AAPL",
        asset_class="equity",
        runtime_mode="fixture",
        delivery="financials",
    )
    news = build_symbol_delivery_contract(
        "AAPL",
        asset_class="equity",
        runtime_mode="fixture",
        delivery="news",
    )
    assert financial["workstations"][0]["identity"]["symbol"] == "AAPL"
    assert news["workstations"][0]["identity"]["symbol"] == "AAPL"
    assert financial_calls == ["AAPL"]
    assert news_calls == ["AAPL"]


def test_phase6d_http_contracts_are_etagged_private_and_isolated(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from backend.api.app import create_app

    db = tmp_path / "watchlists.db"
    monkeypatch.setenv("RESEARCH_WORKSPACE_DB_PATH", str(db))
    client = TestClient(create_app())

    created = client.post("/api/watchlist-desk/lists", json={"name": "Daily", "list_id": "daily"})
    assert created.status_code == 200
    added = client.post(
        "/api/watchlist-desk/lists/daily/items",
        json={
            "symbol": "AAPL",
            "asset_class": "equity",
            "private_reason": PRIVATE_REASON,
        },
    )
    assert added.status_code == 200
    assert PRIVATE_REASON not in added.text
    desk = client.get("/api/watchlist-desk?list_id=daily&selected=AAPL")
    assert desk.status_code == 200
    assert PRIVATE_REASON not in desk.text

    summary = client.get(
        "/api/symbol-workstation/AAPL/summary",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
    )
    assert summary.status_code == 200
    assert summary.headers["etag"]
    assert len(summary.content) < 50_000
    conditional = client.get(
        "/api/symbol-workstation/AAPL/summary",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
        headers={"If-None-Match": summary.headers["etag"]},
    )
    assert conditional.status_code == 304

    unknown = client.get(
        "/api/symbol-workstation/NOTAREAL123/summary",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
    )
    assert unknown.status_code == 404
    assert "Apple" not in unknown.text
    assert "AAPL" not in unknown.text

    ok, issues = validate_api_payload(desk.json())
    assert ok, issues
