from __future__ import annotations

from pathlib import Path
from typing import Any

from .watchlist_store import list_watchlist_items
from .watchlist_data_enricher import enrich_watchlist_items, build_watchlist_context_bundle
from .watchlist_heatmap_adapter import build_watchlist_heatmap_from_enriched
from .watchlist_rmi_adapter import build_watchlist_rmi_from_enriched
from .watchlist_volatility_adapter import build_watchlist_volatility_from_enriched


def build_watchlist_table(db_path: str | Path | None = None, items: list[dict[str, Any]] | None = None, *, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = items if items is not None else list_watchlist_items(db_path=db_path)
    enriched = enrich_watchlist_items(rows, supplied_context=context, db_path=db_path) if context is not None else rows
    return [
        {
            "item_id": row.get("item_id"),
            "type": row.get("item_type"),
            "symbol": row.get("symbol"),
            "name": row.get("display_name"),
            "asset_class": row.get("asset_class"),
            "region": row.get("region"),
            "tags": ", ".join(row.get("tags", [])),
            "source": row.get("source"),
            "source_status": row.get("source_status", "local"),
            "freshness": row.get("freshness", "local"),
            "data_confidence": row.get("data_confidence", "local"),
            "latest_value": row.get("latest_value"),
            "change_pct": row.get("change_pct"),
            "volatility_state": row.get("volatility_state"),
            "rmi_state": row.get("relative_state"),
            "active_alert_count": row.get("active_alert_count", 0),
            "linked_report_count": row.get("linked_report_count", 0),
            "linked_event_count": row.get("linked_event_count", 0),
            "default_command": row.get("default_command"),
        }
        for row in enriched
    ]


def build_watchlist_summary(db_path: str | Path | None = None, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = items if items is not None else list_watchlist_items(db_path=db_path)
    by_type: dict[str, int] = {}
    by_region: dict[str, int] = {}
    source_states: dict[str, int] = {}
    for row in rows:
        by_type[row.get("item_type") or "unknown"] = by_type.get(row.get("item_type") or "unknown", 0) + 1
        region = row.get("region") or "Unspecified"
        by_region[region] = by_region.get(region, 0) + 1
        state = row.get("source_status") or row.get("freshness") or "local"
        source_states[state] = source_states.get(state, 0) + 1
    return {"count": len(rows), "by_type": by_type, "by_region": by_region, "source_states": source_states, "research_only": True}


def build_watchlist_context(db_path: str | Path | None = None, *, supplied_context: dict[str, Any] | None = None) -> dict[str, Any]:
    items = list_watchlist_items(db_path=db_path)
    enriched = enrich_watchlist_items(items, supplied_context=supplied_context, db_path=db_path)
    return {"items": items, "enriched_items": enriched, "table": build_watchlist_table(items=enriched), "summary": build_watchlist_summary(items=enriched), "bundle": build_watchlist_context_bundle(items, supplied_context=supplied_context, db_path=db_path)}


def build_watchlist_heatmap_payload(db_path: str | Path | None = None, items: list[dict[str, Any]] | None = None, *, supplied_context: dict[str, Any] | None = None, color_mode: str = "risk") -> dict[str, Any]:
    rows = items if items is not None else list_watchlist_items(db_path=db_path)
    enriched = enrich_watchlist_items(rows, supplied_context=supplied_context, db_path=db_path)
    payload = build_watchlist_heatmap_from_enriched(enriched, color_mode=color_mode)
    payload.setdefault("fallback_notice", "Rows without supplied market/provider/OSINT context are explicitly labeled unavailable or fallback.")
    return payload


def build_watchlist_rmi_payload(db_path: str | Path | None = None, items: list[dict[str, Any]] | None = None, *, supplied_context: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = items if items is not None else list_watchlist_items(db_path=db_path)
    enriched = enrich_watchlist_items(rows, supplied_context=supplied_context, db_path=db_path)
    return build_watchlist_rmi_from_enriched(enriched)


def build_watchlist_volatility_payload(db_path: str | Path | None = None, items: list[dict[str, Any]] | None = None, *, supplied_context: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = items if items is not None else list_watchlist_items(db_path=db_path)
    enriched = enrich_watchlist_items(rows, supplied_context=supplied_context, db_path=db_path)
    return build_watchlist_volatility_from_enriched(enriched)
