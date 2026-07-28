from __future__ import annotations

import json
import sqlite3

import pytest

from backend.api.app import get_research_memory_payload
from lib.api_contracts import validate_api_payload
from lib.research_memory import (
    append_source_snapshot,
    archive_memory_item,
    build_research_memory_contract,
    build_sanitized_export,
    compare_memory_items,
    get_memory_item,
    list_memory_items,
    origin_href,
    save_memory_item,
    search_memory_items,
)
from lib.research_workspace_migrations import get_workspace_schema_version, run_workspace_migrations
from lib.research_workspace_schema import SCHEMA_VERSION


def test_demo_contract_is_fictional_complete_and_source_bound():
    payload = build_research_memory_contract(mode="demo", collection_id="demo-research", surface="inbox")
    assert payload["research_memory_version"] == "research_memory.v1"
    assert payload["summary"] == {
        "item_count": 4,
        "watchlist_count": 3,
        "report_count": 1,
        "source_count": 2,
        "source_status": "fixture",
        "store_status": "ready",
    }
    assert all(row["privacy_scope"] == "fictional-demo" for row in payload["items"])
    assert all(row["provider"] and row["source_status"] and row["caveat"] for row in payload["source_history"])
    assert payload["privacy"]["external_ai_enabled"] is False


def test_schema_v4_migrates_and_crud_search_is_bounded(tmp_path):
    db = tmp_path / "memory.db"
    run_workspace_migrations(db)
    assert get_workspace_schema_version(db) == SCHEMA_VERSION
    assert SCHEMA_VERSION >= 7
    saved = save_memory_item(
        collection_id="local-research",
        memory_type="note",
        title="Private thesis title",
        private_body="A private body containing duration sensitivity.",
        origin_id="aapl-equity",
        compatibility_period="1y",
        compatibility_model="cross-asset-v1",
        linked_symbols=["AAPL", "TLT"],
        tags=["macro", "rates"],
        db_path=db,
    )
    assert saved["private_body"].startswith("A private")
    assert get_memory_item(saved["memory_id"], db_path=db).get("private_body") is None
    results = search_memory_items("duration", collection_id="local-research", limit=9999, db_path=db)
    assert [row["memory_id"] for row in results] == [saved["memory_id"]]
    assert results[0].get("private_body") is None
    assert len(list_memory_items(collection_id="local-research", limit=9999, db_path=db)) <= 100
    assert archive_memory_item(saved["memory_id"], db_path=db)
    assert list_memory_items(collection_id="local-research", db_path=db) == []


def test_duplicate_ids_and_invalid_origins_are_rejected(tmp_path):
    db = tmp_path / "duplicates.db"
    kwargs = dict(collection_id="local-research", memory_type="note", title="one", memory_id="memory_fixed", db_path=db)
    save_memory_item(**kwargs)
    with pytest.raises(ValueError, match="Duplicate memory_id"):
        save_memory_item(**kwargs)
    with pytest.raises(ValueError, match="Unknown origin_id"):
        save_memory_item(collection_id="local-research", memory_type="note", title="bad", origin_id="../../secret", db_path=db)


def test_source_history_is_append_only_and_does_not_rewrite_failure_as_live(tmp_path):
    db = tmp_path / "sources.db"
    item = save_memory_item(collection_id="local-research", memory_type="snapshot", title="source test", db_path=db)
    first = append_source_snapshot(
        item["memory_id"], provider="public-rss", source_status="live/fresh", freshness="fresh",
        confidence=0.8, snapshot_id="source_one", db_path=db,
    )
    append_source_snapshot(
        item["memory_id"], provider="public-rss", source_status="stale", freshness="stale",
        confidence=0.4, snapshot_id="source_two", data_gap="Provider timed out.", db_path=db,
    )
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT source_status FROM research_source_history WHERE snapshot_id = ?", (first["snapshot_id"],)).fetchone()
        assert row == ("live/fresh",)
        assert conn.execute("SELECT COUNT(*) FROM research_source_history").fetchone() == (2,)


def test_compare_requires_exact_period_and_model_labels(tmp_path):
    db = tmp_path / "compare.db"
    a = save_memory_item(collection_id="local-research", memory_type="snapshot", title="a", compatibility_period="1y", compatibility_model="model-v1", db_path=db)
    b = save_memory_item(collection_id="local-research", memory_type="snapshot", title="b", compatibility_period="1y", compatibility_model="model-v1", db_path=db)
    c = save_memory_item(collection_id="local-research", memory_type="snapshot", title="c", compatibility_period="3mo", compatibility_model="model-v1", db_path=db)
    assert compare_memory_items([a["memory_id"], b["memory_id"]], db_path=db)["compatible"] is True
    assert compare_memory_items([a["memory_id"], c["memory_id"]], db_path=db)["compatible"] is False


def test_sanitized_export_excludes_private_body_titles_symbols_and_paths(tmp_path):
    db = tmp_path / "export.db"
    item = save_memory_item(
        collection_id="local-research", memory_type="note", title="Secret merger thought",
        private_body="Do not disclose this text", linked_symbols=["PRIVATE1"], db_path=db,
    )
    append_source_snapshot(item["memory_id"], provider="fixture", source_status="fixture", db_path=db)
    payload = build_sanitized_export(collection_id="local-research", db_path=db)
    encoded = json.dumps(payload)
    assert "Secret merger" not in encoded
    assert "Do not disclose" not in encoded
    assert "PRIVATE1" not in encoded
    assert str(tmp_path) not in encoded
    assert payload["privacy_scope"] == "sanitized-metadata"


def test_local_contract_handles_corrupt_store_honestly(tmp_path):
    db = tmp_path / "corrupt.db"
    db.write_bytes(b"not sqlite")
    payload = build_research_memory_contract(mode="local", collection_id="local-research", db_path=db)
    assert payload["summary"]["source_status"] == "unavailable"
    assert payload["readiness"]["store_status"] == "corrupt-or-unavailable"
    assert payload["items"] == []


def test_origin_links_are_whitelisted_and_never_contain_private_text():
    assert origin_href("aapl-equity") == "/?view=asset&symbol=AAPL&assetClass=equity&timeframe=1D&surface=overview"
    assert origin_href("unknown") is None


def test_api_envelope_is_json_safe_and_demo_fixture_has_no_private_store_path():
    payload = get_research_memory_payload(mode="demo", collection_id="demo-research", surface="sources")
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    assert payload["payload_type"] == "research_memory"
    encoded = json.dumps(payload)
    assert "data/private" not in encoded
    assert "research_workspace.db" not in encoded
    assert payload["data"]["privacy"]["scope"] == "fictional-demo"


def test_fastapi_local_save_search_source_watchlist_and_export_workflow(tmp_path, monkeypatch):
    try:
        from fastapi.testclient import TestClient
        from backend.api import app as backend_app
    except Exception as exc:  # pragma: no cover - optional dependency stack
        pytest.skip(str(exc))
    monkeypatch.setenv("RESEARCH_WORKSPACE_DB_PATH", str(tmp_path / "api-memory.db"))
    client = TestClient(backend_app.app)
    private_needle = "never-url-private-needle"
    created = client.post(
        "/api/research-memory/items",
        json={
            "collection_id": "local-research",
            "memory_type": "note",
            "title": "Private API title",
            "private_body": private_needle,
            "origin_id": "aapl-equity",
            "linked_symbols": ["PRIVATE2"],
            "tags": ["local-note"],
        },
    )
    assert created.status_code == 200
    memory_id = created.json()["item"]["memory_id"]
    assert private_needle not in str(created.request.url)

    searched = client.post(
        "/api/research-memory/search",
        json={"query": private_needle, "collection_id": "local-research"},
    )
    assert searched.status_code == 200
    assert searched.json()["query_transport"] == "POST-body"
    assert searched.json()["items"][0]["memory_id"] == memory_id
    assert private_needle not in str(searched.request.url)

    source = client.post(
        "/api/research-memory/source-snapshots",
        json={"memory_id": memory_id, "provider": "fixture", "source_status": "stale", "data_gap": "test gap"},
    )
    assert source.status_code == 200

    watched = client.post(
        "/api/research-memory/watchlists",
        json={"symbol": "AAPL", "display_name": "Apple", "item_type": "equity"},
    )
    assert watched.status_code == 200
    watch_id = watched.json()["item"]["item_id"]
    assert client.delete(f"/api/research-memory/watchlists/{watch_id}").json()["ok"] is True

    exported = client.post("/api/research-memory/export", json={"collection_id": "local-research"})
    encoded = json.dumps(exported.json())
    assert exported.status_code == 200
    assert private_needle not in encoded
    assert "Private API title" not in encoded
    assert "PRIVATE2" not in encoded
