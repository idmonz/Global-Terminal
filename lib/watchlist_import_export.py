from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .watchlist_store import create_watchlist_item, list_watchlist_items


def export_watchlist_items(path: str | Path | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    rows = list_watchlist_items(db_path=db_path)
    payload = {"watchlist_items": rows, "count": len(rows), "research_only": True}
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def import_watchlist_items(payload: dict[str, Any], db_path: str | Path | None = None) -> list[dict[str, Any]]:
    imported = []
    for row in payload.get("watchlist_items", []):
        imported.append(create_watchlist_item(
            item_type=row.get("item_type", "asset"), symbol=row.get("symbol", ""), display_name=row.get("display_name"),
            asset_class=row.get("asset_class", ""), exchange=row.get("exchange", ""), region=row.get("region", ""),
            country=row.get("country", ""), tags=row.get("tags", []), watch_reason=row.get("watch_reason", ""),
            default_command=row.get("default_command", ""), default_page=row.get("default_page", "pages/20_Watchlist_Alerts.py"),
            source="import", active=bool(row.get("active", True)), metadata=row.get("metadata_json", {}), db_path=db_path,
        ))
    return imported

