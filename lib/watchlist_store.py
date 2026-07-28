from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now
from .watchlist_models import validate_watchlist_item_type


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["tags"] = json_loads(out.get("tags"), [])
    out["metadata_json"] = json_loads(out.get("metadata_json"), {})
    out["active"] = bool(out.get("active"))
    out["position"] = int(out.get("position") or 0)
    return out


def create_watchlist_item(
    *,
    item_type: str = "asset",
    watchlist_id: str = "primary",
    position: int = 0,
    symbol: str = "",
    display_name: str | None = None,
    asset_class: str = "",
    exchange: str = "",
    region: str = "",
    country: str = "",
    tags: list[str] | None = None,
    watch_reason: str = "",
    default_command: str = "",
    default_page: str = "pages/20_Watchlist_Alerts.py",
    source: str = "manual",
    active: bool = True,
    metadata: dict[str, Any] | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    now = utc_now()
    normalized_type = validate_watchlist_item_type(item_type)
    row = {
        "item_id": new_id("watch"),
        "watchlist_id": str(watchlist_id or "primary"),
        "position": max(0, int(position)),
        "item_type": normalized_type,
        "symbol": symbol,
        "display_name": display_name or symbol or normalized_type.title(),
        "asset_class": asset_class or normalized_type,
        "exchange": exchange,
        "region": region,
        "country": country,
        "tags": json_dumps(tags or []),
        "watch_reason": watch_reason,
        "default_command": default_command or (f"{symbol} WATCH" if symbol else "WATCHLIST"),
        "default_page": default_page,
        "source": source,
        "active": 1 if active else 0,
        "created_at": now,
        "updated_at": now,
        "metadata_json": json_dumps(metadata or {}),
    }
    execute_query(
        """
        INSERT INTO watchlist_items (
            item_id, watchlist_id, position, item_type, symbol, display_name, asset_class, exchange, region, country,
            tags, watch_reason, default_command, default_page, source, active, created_at, updated_at, metadata_json
        ) VALUES (:item_id, :watchlist_id, :position, :item_type, :symbol, :display_name, :asset_class, :exchange, :region, :country,
            :tags, :watch_reason, :default_command, :default_page, :source, :active, :created_at, :updated_at, :metadata_json)
        """,
        row,
        db_path=db_path,
    )
    return get_watchlist_item(row["item_id"], db_path) or _decode(row)


def get_watchlist_item(item_id: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    row = execute_query("SELECT * FROM watchlist_items WHERE item_id = ?", (item_id,), fetch=True, one=True, db_path=db_path)
    return _decode(row) if isinstance(row, dict) else None


def update_watchlist_item(item_id: str, db_path: str | Path | None = None, **updates: Any) -> dict[str, Any] | None:
    existing = get_watchlist_item(item_id, db_path)
    if not existing:
        return None
    allowed = {"watchlist_id", "position", "item_type", "symbol", "display_name", "asset_class", "exchange", "region", "country", "tags", "watch_reason", "default_command", "default_page", "source", "active", "metadata_json"}
    row = {k: v for k, v in updates.items() if k in allowed}
    if "item_type" in row:
        row["item_type"] = validate_watchlist_item_type(row["item_type"])
    if "tags" in row:
        row["tags"] = json_dumps(row["tags"])
    if "metadata_json" in row and not isinstance(row["metadata_json"], str):
        row["metadata_json"] = json_dumps(row["metadata_json"])
    if "active" in row:
        row["active"] = 1 if row["active"] else 0
    if "position" in row:
        row["position"] = max(0, int(row["position"]))
    row["updated_at"] = utc_now()
    row["item_id"] = item_id
    assignments = ", ".join(f"{key} = :{key}" for key in row if key != "item_id")
    execute_query(f"UPDATE watchlist_items SET {assignments} WHERE item_id = :item_id", row, db_path=db_path)
    return get_watchlist_item(item_id, db_path)


def delete_watchlist_item(item_id: str, db_path: str | Path | None = None) -> bool:
    execute_query("UPDATE watchlist_items SET active = 0, updated_at = ? WHERE item_id = ?", (utc_now(), item_id), db_path=db_path)
    return True


def list_watchlist_items(active_only: bool = True, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    where = "WHERE active = 1" if active_only else ""
    rows = execute_query(f"SELECT * FROM watchlist_items {where} ORDER BY updated_at DESC", fetch=True, db_path=db_path)
    return [_decode(row) for row in rows]  # type: ignore[arg-type]


def search_watchlist_items(query: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    needle = f"%{str(query or '').lower()}%"
    rows = execute_query(
        """
        SELECT * FROM watchlist_items
        WHERE active = 1 AND (
            lower(symbol) LIKE ? OR lower(display_name) LIKE ? OR lower(region) LIKE ? OR lower(country) LIKE ? OR lower(tags) LIKE ?
        ) ORDER BY updated_at DESC
        """,
        (needle, needle, needle, needle, needle),
        fetch=True,
        db_path=db_path,
    )
    return [_decode(row) for row in rows]  # type: ignore[arg-type]


def tag_watchlist_item(item_id: str, tag: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    item = get_watchlist_item(item_id, db_path)
    if not item:
        return None
    tags = list(dict.fromkeys([*item.get("tags", []), str(tag)]))
    return update_watchlist_item(item_id, db_path, tags=tags)
