from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

from .report_inbox import list_reports
from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now
from .research_workspace_migrations import run_workspace_migrations
from .watchlist_store import create_watchlist_item, delete_watchlist_item, list_watchlist_items


RESEARCH_MEMORY_VERSION = "research_memory.v1"
MEMORY_TYPES = {"note", "snapshot", "report", "event", "source"}
SURFACES = {"inbox", "watchlists", "notes", "reports", "sources"}
MODES = {"demo", "local"}
MAX_RESULTS = 100
OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
SAFE_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,31}$")
DYNAMIC_ASSET_ORIGIN = re.compile(r"^asset-(equity|etf|crypto)-([A-Z0-9._-]{1,24})$")

ORIGIN_REGISTRY: dict[str, dict[str, str]] = {
    "aapl-equity": {"label": "AAPL Equity", "view": "asset", "symbol": "AAPL", "assetClass": "equity", "timeframe": "1D", "surface": "overview"},
    "btcusdt-crypto": {"label": "BTCUSDT Crypto", "view": "asset", "symbol": "BTCUSDT", "assetClass": "crypto", "timeframe": "1D", "surface": "overview"},
    "war-map": {"label": "Global Risk Map", "view": "war-room-map"},
    "market-map": {"label": "Market Map", "view": "market-map"},
    "aapl-options": {"label": "AAPL Options", "view": "options-quant", "symbol": "AAPL", "surface": "chain"},
    "demo-portfolio": {"label": "Demo Portfolio", "view": "portfolio-risk", "portfolio": "demo-core", "surface": "overview", "period": "1y", "benchmark": "SPY"},
}


def _clean_text(value: Any, *, limit: int, fallback: str = "") -> str:
    text = str(value if value is not None else fallback).replace("\x00", " ").strip()
    return text[:limit] or fallback


def _opaque_id(value: Any, *, fallback: str) -> str:
    text = _clean_text(value, limit=96, fallback=fallback)
    if not OPAQUE_ID.fullmatch(text):
        raise ValueError("Identifier must be opaque and URL-safe.")
    return text


def _normalize_tags(values: Iterable[Any] | None) -> list[str]:
    tags: list[str] = []
    for value in values or []:
        tag = _clean_text(value, limit=32)
        if tag and SAFE_TAG.fullmatch(tag) and tag not in tags:
            tags.append(tag)
    return tags[:12]


def _normalize_symbols(values: Iterable[Any] | None) -> list[str]:
    symbols: list[str] = []
    for value in values or []:
        symbol = re.sub(r"[^A-Z0-9.=_-]", "", str(value or "").upper())[:24]
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols[:20]


def origin_href(origin_id: str) -> str | None:
    current = str(origin_id or "")
    origin = ORIGIN_REGISTRY.get(current)
    if not origin:
        match = DYNAMIC_ASSET_ORIGIN.fullmatch(current)
        if match:
            asset_class, symbol = match.groups()
            origin = {
                "view": "asset",
                "symbol": symbol,
                "assetClass": asset_class,
                "interval": "1d",
                "range": "3mo",
                "surface": "overview",
            }
    if not origin:
        return None
    params = {key: value for key, value in origin.items() if key != "label"}
    return "/?" + urlencode(params)


def _decode_item(row: dict[str, Any], *, include_private: bool = False) -> dict[str, Any]:
    item = dict(row)
    for key in ("origin_context_json", "metadata_json"):
        item[key] = json_loads(item.get(key), {})
    for key in ("linked_symbols_json", "linked_events_json", "linked_reports_json", "tags_json"):
        item[key] = json_loads(item.get(key), [])
    item["archived"] = bool(item.get("archived"))
    item["origin_href"] = origin_href(str(item.get("origin_view") or ""))
    item["privacy_scope"] = "local-private"
    if not include_private:
        item.pop("private_body", None)
    return item


def save_memory_item(
    *,
    collection_id: str = "local-research",
    memory_type: str,
    title: str,
    private_body: str = "",
    sanitized_summary: str = "",
    origin_id: str = "",
    compatibility_period: str = "",
    compatibility_model: str = "",
    linked_symbols: Iterable[Any] | None = None,
    linked_events: Iterable[Any] | None = None,
    linked_reports: Iterable[Any] | None = None,
    tags: Iterable[Any] | None = None,
    metadata: dict[str, Any] | None = None,
    memory_id: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    run_workspace_migrations(db_path)
    normalized_type = str(memory_type or "").lower().strip()
    if normalized_type not in MEMORY_TYPES:
        raise ValueError(f"Unsupported memory_type: {memory_type}")
    collection = _opaque_id(collection_id, fallback="local-research")
    item_id = _opaque_id(memory_id, fallback=new_id("memory")) if memory_id else new_id("memory")
    origin = _clean_text(origin_id, limit=64)
    if origin and origin_href(origin) is None:
        raise ValueError("Unknown origin_id.")
    period = _clean_text(compatibility_period, limit=32)
    model = _clean_text(compatibility_model, limit=64)
    compatibility_key = f"{normalized_type}:{period or 'na'}:{model or 'na'}"
    now = utc_now()
    row = {
        "memory_id": item_id,
        "collection_id": collection,
        "memory_type": normalized_type,
        "title": _clean_text(title, limit=160, fallback=normalized_type.title()),
        "private_body": _clean_text(private_body, limit=50000),
        "sanitized_summary": _clean_text(sanitized_summary, limit=240, fallback="Local research item; private body omitted from public boundaries."),
        "origin_view": origin,
        "origin_context_json": json_dumps({"origin_id": origin} if origin else {}),
        "compatibility_period": period,
        "compatibility_model": model,
        "compatibility_key": compatibility_key,
        "linked_symbols_json": json_dumps(_normalize_symbols(linked_symbols)),
        "linked_events_json": json_dumps([_opaque_id(value, fallback="event") for value in list(linked_events or [])[:20]]),
        "linked_reports_json": json_dumps([_opaque_id(value, fallback="report") for value in list(linked_reports or [])[:20]]),
        "tags_json": json_dumps(_normalize_tags(tags)),
        "status": "active",
        "archived": 0,
        "created_at": now,
        "updated_at": now,
        "metadata_json": json_dumps(metadata or {}),
    }
    try:
        execute_query(
            """
            INSERT INTO research_memory_items (
                memory_id, collection_id, memory_type, title, private_body, sanitized_summary,
                origin_view, origin_context_json, compatibility_period, compatibility_model,
                compatibility_key, linked_symbols_json, linked_events_json, linked_reports_json,
                tags_json, status, archived, created_at, updated_at, metadata_json
            ) VALUES (
                :memory_id, :collection_id, :memory_type, :title, :private_body, :sanitized_summary,
                :origin_view, :origin_context_json, :compatibility_period, :compatibility_model,
                :compatibility_key, :linked_symbols_json, :linked_events_json, :linked_reports_json,
                :tags_json, :status, :archived, :created_at, :updated_at, :metadata_json
            )
            """,
            row,
            db_path=db_path,
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Duplicate memory_id: {item_id}") from exc
    return get_memory_item(item_id, include_private=True, db_path=db_path) or _decode_item(row, include_private=True)


def get_memory_item(memory_id: str, *, include_private: bool = False, db_path: str | Path | None = None) -> dict[str, Any] | None:
    item_id = _opaque_id(memory_id, fallback="memory")
    row = execute_query("SELECT * FROM research_memory_items WHERE memory_id = ?", (item_id,), fetch=True, one=True, db_path=db_path)
    return _decode_item(row, include_private=include_private) if isinstance(row, dict) else None


def list_memory_items(
    *, collection_id: str = "local-research", memory_type: str = "", tag: str = "", limit: int = 50,
    include_private: bool = False, db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    collection = _opaque_id(collection_id, fallback="local-research")
    clauses = ["collection_id = ?", "archived = 0"]
    params: list[Any] = [collection]
    if memory_type:
        normalized_type = str(memory_type).lower().strip()
        if normalized_type not in MEMORY_TYPES:
            raise ValueError("Unsupported memory_type filter.")
        clauses.append("memory_type = ?")
        params.append(normalized_type)
    if tag:
        safe_tag = _normalize_tags([tag])
        if not safe_tag:
            raise ValueError("Invalid tag filter.")
        clauses.append("lower(tags_json) LIKE ?")
        params.append(f'%"{safe_tag[0].lower()}"%')
    bounded = max(1, min(int(limit), MAX_RESULTS))
    params.append(bounded)
    rows = execute_query(
        f"SELECT * FROM research_memory_items WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC, memory_id ASC LIMIT ?",
        params,
        fetch=True,
        db_path=db_path,
    )
    return [_decode_item(row, include_private=include_private) for row in rows]  # type: ignore[arg-type]


def search_memory_items(
    query: str, *, collection_id: str = "local-research", limit: int = 50,
    include_private: bool = False, db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    collection = _opaque_id(collection_id, fallback="local-research")
    needle = _clean_text(query, limit=160).lower()
    if not needle:
        return list_memory_items(collection_id=collection, limit=limit, include_private=include_private, db_path=db_path)
    like = f"%{needle}%"
    bounded = max(1, min(int(limit), MAX_RESULTS))
    rows = execute_query(
        """
        SELECT * FROM research_memory_items
        WHERE collection_id = ? AND archived = 0 AND (
            lower(title) LIKE ? OR lower(private_body) LIKE ? OR lower(tags_json) LIKE ? OR lower(linked_symbols_json) LIKE ?
        ) ORDER BY updated_at DESC, memory_id ASC LIMIT ?
        """,
        (collection, like, like, like, like, bounded),
        fetch=True,
        db_path=db_path,
    )
    return [_decode_item(row, include_private=include_private) for row in rows]  # type: ignore[arg-type]


def archive_memory_item(memory_id: str, *, db_path: str | Path | None = None) -> bool:
    item_id = _opaque_id(memory_id, fallback="memory")
    count = execute_query(
        "UPDATE research_memory_items SET archived = 1, status = 'archived', updated_at = ? WHERE memory_id = ?",
        (utc_now(), item_id),
        db_path=db_path,
    )
    return bool(count)


def append_source_snapshot(
    memory_id: str, *, provider: str, source_url: str = "", fetched_at: str | None = None,
    freshness: str = "unknown", source_status: str = "unknown", confidence: float = 0.0,
    caveat: str = "", data_gap: str = "", metadata: dict[str, Any] | None = None,
    snapshot_id: str | None = None, db_path: str | Path | None = None,
) -> dict[str, Any]:
    item_id = _opaque_id(memory_id, fallback="memory")
    if not get_memory_item(item_id, db_path=db_path):
        raise ValueError("Source snapshot requires an existing memory item.")
    row = {
        "snapshot_id": _opaque_id(snapshot_id, fallback=new_id("source")) if snapshot_id else new_id("source"),
        "memory_id": item_id,
        "provider": _clean_text(provider, limit=80, fallback="unknown"),
        "source_url": _clean_text(source_url, limit=1000),
        "fetched_at": _clean_text(fetched_at, limit=64) if fetched_at else None,
        "freshness": _clean_text(freshness, limit=32, fallback="unknown"),
        "source_status": _clean_text(source_status, limit=48, fallback="unknown"),
        "confidence": max(0.0, min(float(confidence), 1.0)),
        "caveat": _clean_text(caveat, limit=1000),
        "data_gap": _clean_text(data_gap, limit=1000),
        "captured_at": utc_now(),
        "metadata_json": json_dumps(metadata or {}),
    }
    try:
        execute_query(
            """INSERT INTO research_source_history (
                snapshot_id, memory_id, provider, source_url, fetched_at, freshness, source_status,
                confidence, caveat, data_gap, captured_at, metadata_json
            ) VALUES (:snapshot_id, :memory_id, :provider, :source_url, :fetched_at, :freshness, :source_status,
                :confidence, :caveat, :data_gap, :captured_at, :metadata_json)""",
            row,
            db_path=db_path,
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Duplicate snapshot_id: {row['snapshot_id']}") from exc
    row["metadata_json"] = metadata or {}
    return row


def list_source_history(memory_id: str | None = None, *, limit: int = 100, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    bounded = max(1, min(int(limit), MAX_RESULTS))
    if memory_id:
        item_id = _opaque_id(memory_id, fallback="memory")
        rows = execute_query(
            "SELECT * FROM research_source_history WHERE memory_id = ? ORDER BY captured_at DESC, snapshot_id ASC LIMIT ?",
            (item_id, bounded), fetch=True, db_path=db_path,
        )
    else:
        rows = execute_query(
            "SELECT * FROM research_source_history ORDER BY captured_at DESC, snapshot_id ASC LIMIT ?",
            (bounded,), fetch=True, db_path=db_path,
        )
    output = []
    for row in rows:  # type: ignore[union-attr]
        decoded = dict(row)
        decoded["metadata_json"] = json_loads(decoded.get("metadata_json"), {})
        output.append(decoded)
    return output


def compare_memory_items(memory_ids: Iterable[str], *, db_path: str | Path | None = None) -> dict[str, Any]:
    items = [get_memory_item(item_id, db_path=db_path) for item_id in list(memory_ids)[:4]]
    rows = [item for item in items if item]
    keys = {str(item.get("compatibility_key") or "") for item in rows}
    compatible = len(rows) > 1 and len(keys) == 1 and "" not in keys
    return {
        "item_count": len(rows),
        "compatible": compatible,
        "compatibility_key": next(iter(keys)) if compatible else None,
        "reason": "Periods and models match." if compatible else "Comparison requires matching memory type, period, and model labels.",
        "items": [{key: item.get(key) for key in ("memory_id", "memory_type", "compatibility_period", "compatibility_model", "compatibility_key")} for item in rows],
    }


def build_sanitized_export(*, collection_id: str = "local-research", db_path: str | Path | None = None) -> dict[str, Any]:
    items = list_memory_items(collection_id=collection_id, limit=MAX_RESULTS, db_path=db_path)
    item_ids = {str(item.get("memory_id")) for item in items}
    sources = [row for row in list_source_history(limit=MAX_RESULTS, db_path=db_path) if str(row.get("memory_id")) in item_ids]
    return {
        "export_version": "research_memory.sanitized.v1",
        "collection_id": _opaque_id(collection_id, fallback="local-research"),
        "privacy_scope": "sanitized-metadata",
        "items": [
            {
                "memory_id": item.get("memory_id"),
                "memory_type": item.get("memory_type"),
                "origin_id": item.get("origin_view"),
                "compatibility_period": item.get("compatibility_period"),
                "compatibility_model": item.get("compatibility_model"),
                "status": item.get("status"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            }
            for item in items
        ],
        "source_history": [
            {key: row.get(key) for key in ("snapshot_id", "memory_id", "provider", "source_url", "fetched_at", "freshness", "source_status", "confidence", "caveat", "data_gap", "captured_at")}
            for row in sources
        ],
        "excluded_fields": ["title", "private_body", "sanitized_summary", "linked_symbols", "watchlist symbols", "attachments", "local paths", "account data"],
        "disclosure": "Sanitized metadata only. Private notes, symbols, holdings, attachments, report bodies, account data, and local paths are excluded.",
    }


def _demo_contract() -> dict[str, Any]:
    items = [
        {"memory_id": "demo_macro_note", "collection_id": "demo-research", "memory_type": "note", "title": "Rate sensitivity review", "sanitized_summary": "Fictional note linking duration and equity sensitivity.", "origin_view": "aapl-equity", "origin_href": origin_href("aapl-equity"), "compatibility_period": "1y", "compatibility_model": "cross-asset-v1", "compatibility_key": "note:1y:cross-asset-v1", "linked_symbols_json": ["AAPL", "TLT"], "linked_events_json": [], "linked_reports_json": [], "tags_json": ["macro", "rates"], "status": "active", "created_at": "2026-06-20T09:00:00+00:00", "updated_at": "2026-06-21T06:15:00+00:00", "privacy_scope": "fictional-demo"},
        {"memory_id": "demo_map_snapshot", "collection_id": "demo-research", "memory_type": "snapshot", "title": "Red Sea source check", "sanitized_summary": "Fictional snapshot retaining map source caveats.", "origin_view": "war-map", "origin_href": origin_href("war-map"), "compatibility_period": "24h", "compatibility_model": "map-event-v1", "compatibility_key": "snapshot:24h:map-event-v1", "linked_symbols_json": ["CL=F"], "linked_events_json": ["demo_red_sea"], "linked_reports_json": [], "tags_json": ["geopolitics", "energy"], "status": "active", "created_at": "2026-06-20T12:00:00+00:00", "updated_at": "2026-06-21T05:45:00+00:00", "privacy_scope": "fictional-demo"},
        {"memory_id": "demo_options_snapshot", "collection_id": "demo-research", "memory_type": "snapshot", "title": "AAPL volatility surface", "sanitized_summary": "Fictional options snapshot with expiry and model labels.", "origin_view": "aapl-options", "origin_href": origin_href("aapl-options"), "compatibility_period": "2026-07-17", "compatibility_model": "black-scholes-v1", "compatibility_key": "snapshot:2026-07-17:black-scholes-v1", "linked_symbols_json": ["AAPL"], "linked_events_json": [], "linked_reports_json": [], "tags_json": ["options", "volatility"], "status": "active", "created_at": "2026-06-19T15:00:00+00:00", "updated_at": "2026-06-20T22:30:00+00:00", "privacy_scope": "fictional-demo"},
        {"memory_id": "demo_portfolio_report", "collection_id": "demo-research", "memory_type": "report", "title": "Demo portfolio risk review", "sanitized_summary": "Fictional holdings-free portfolio report metadata.", "origin_view": "demo-portfolio", "origin_href": origin_href("demo-portfolio"), "compatibility_period": "1y", "compatibility_model": "portfolio.v1", "compatibility_key": "report:1y:portfolio.v1", "linked_symbols_json": [], "linked_events_json": [], "linked_reports_json": ["demo_report"], "tags_json": ["portfolio", "risk"], "status": "reviewed", "created_at": "2026-06-18T08:00:00+00:00", "updated_at": "2026-06-20T08:00:00+00:00", "privacy_scope": "fictional-demo"},
    ]
    watchlists = [
        {"item_id": "demo_watch_aapl", "display_name": "Apple", "symbol": "AAPL", "item_type": "equity", "watch_reason": "Fictional earnings-quality review", "tags": ["quality"], "origin_href": origin_href("aapl-equity"), "source": "fictional-demo", "updated_at": "2026-06-21T06:00:00+00:00"},
        {"item_id": "demo_watch_btc", "display_name": "Bitcoin", "symbol": "BTCUSDT", "item_type": "crypto", "watch_reason": "Fictional derivatives monitoring", "tags": ["crypto"], "origin_href": origin_href("btcusdt-crypto"), "source": "fictional-demo", "updated_at": "2026-06-21T05:30:00+00:00"},
        {"item_id": "demo_watch_red_sea", "display_name": "Red Sea", "symbol": "", "item_type": "chokepoint", "watch_reason": "Fictional shipping-risk context", "tags": ["geopolitics"], "origin_href": origin_href("war-map"), "source": "fictional-demo", "updated_at": "2026-06-20T18:00:00+00:00"},
    ]
    sources = [
        {"snapshot_id": "demo_source_yahoo", "memory_id": "demo_macro_note", "provider": "Yahoo Finance", "source_url": "https://finance.yahoo.com/quote/AAPL", "fetched_at": "2026-06-21T06:00:00+00:00", "freshness": "delayed", "source_status": "fixture", "confidence": 0.42, "caveat": "Fictional deterministic source-history row.", "data_gap": "No live provider call in fixture mode.", "captured_at": "2026-06-21T06:15:00+00:00"},
        {"snapshot_id": "demo_source_news", "memory_id": "demo_map_snapshot", "provider": "public-rss", "source_url": "https://example.com/fictional-source", "fetched_at": "2026-06-21T05:30:00+00:00", "freshness": "fixture", "source_status": "fixture", "confidence": 0.4, "caveat": "Fictional source used only for deterministic UI development.", "data_gap": "No live vessel or sanctions feed.", "captured_at": "2026-06-21T05:45:00+00:00"},
    ]
    return {"items": items, "watchlists": watchlists, "reports": [item for item in items if item["memory_type"] == "report"], "source_history": sources}


def build_research_memory_contract(
    *, mode: str = "demo", collection_id: str = "demo-research", surface: str = "inbox",
    memory_type: str = "", tag: str = "", db_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_mode = str(mode or "demo").lower()
    normalized_surface = str(surface or "inbox").lower()
    if normalized_mode not in MODES:
        raise ValueError("mode must be demo or local")
    if normalized_surface not in SURFACES:
        raise ValueError("Unsupported research-memory surface")
    collection = _opaque_id(collection_id, fallback="demo-research" if normalized_mode == "demo" else "local-research")
    store_status = "ready"
    error = None
    if normalized_mode == "demo":
        data = _demo_contract()
    else:
        try:
            run_workspace_migrations(db_path)
            items = list_memory_items(collection_id=collection, memory_type=memory_type, tag=tag, db_path=db_path)
            watchlists = list_watchlist_items(db_path=db_path)
            reports = list_reports(limit=50, db_path=db_path)
            sources = list_source_history(limit=MAX_RESULTS, db_path=db_path)
            data = {"items": items, "watchlists": watchlists, "reports": [{key: row.get(key) for key in ("report_id", "report_type", "title", "summary", "generated_at", "data_confidence", "report_review_status", "tags")} for row in reports], "source_history": sources}
        except (sqlite3.DatabaseError, OSError, ValueError) as exc:
            data = {"items": [], "watchlists": [], "reports": [], "source_history": []}
            store_status = "corrupt-or-unavailable"
            error = type(exc).__name__
    items = data["items"]
    source_rows = data["source_history"]
    return {
        "research_memory_version": RESEARCH_MEMORY_VERSION,
        "workspace": "research-memory",
        "mode": normalized_mode,
        "surface": normalized_surface,
        "collection_id": collection,
        **data,
        "origin_registry": [{"origin_id": key, "label": value["label"], "href": origin_href(key)} for key, value in ORIGIN_REGISTRY.items()],
        "filters": {"memory_types": sorted(MEMORY_TYPES), "surfaces": sorted(SURFACES), "tags": sorted({tag for item in items for tag in item.get("tags_json", [])})},
        "export_preview": {
            "privacy_scope": "sanitized-metadata",
            "item_count": len(items),
            "source_count": len(source_rows),
            "excluded_fields": ["private note body", "holdings", "account data", "attachments", "local paths"],
        },
        "readiness": {
            "store_status": store_status,
            "local_persistence": normalized_mode == "local" and store_status == "ready",
            "external_ai": "disabled",
            "cloud_sync": "unavailable",
            "hosted_auth": "unavailable",
            "error": error,
        },
        "privacy": {
            "scope": "fictional-demo" if normalized_mode == "demo" else "local-private",
            "search_transport": "POST body only",
            "url_private_content_allowed": False,
            "fixture_private_content_allowed": False,
            "release_archive_private_content_allowed": False,
            "external_ai_enabled": False,
        },
        "summary": {
            "item_count": len(items),
            "watchlist_count": len(data["watchlists"]),
            "report_count": len(data["reports"]),
            "source_count": len(source_rows),
            "source_status": "fixture" if normalized_mode == "demo" else ("local-private" if store_status == "ready" else "unavailable"),
            "store_status": store_status,
        },
        "caveat": "Research Memory is a local research archive. It does not provide investment advice, autonomous monitoring, broker actions, or cloud synchronization.",
    }


def add_local_watchlist_item(*, symbol: str, display_name: str = "", item_type: str = "asset", watch_reason: str = "Research monitoring", tags: list[str] | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    return create_watchlist_item(symbol=_normalize_symbols([symbol])[0] if _normalize_symbols([symbol]) else "", display_name=_clean_text(display_name, limit=120) or symbol, item_type=item_type, watch_reason=_clean_text(watch_reason, limit=500), tags=_normalize_tags(tags), source="research-memory-local", db_path=db_path)


def remove_local_watchlist_item(item_id: str, *, db_path: str | Path | None = None) -> bool:
    return delete_watchlist_item(_opaque_id(item_id, fallback="watch"), db_path=db_path)
