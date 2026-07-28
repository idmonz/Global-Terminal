from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now
from .research_workspace_migrations import run_workspace_migrations


SAVED_SCREEN_VERSION = "saved_market_screen.v1"
SCREEN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,79}$")
SCREEN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$")
SECTOR_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &/.-]{0,63}$")
ALLOWED_KEYS = {
    "universe",
    "sectors",
    "market_cap",
    "return_1d",
    "return_1m",
    "volatility",
    "rsi",
    "trend",
    "valuation",
    "quality",
    "rank",
    "display",
}
ENUMS = {
    "universe": {"bounded-us-largecap"},
    "market_cap": {"all", "mega", "large", "mid"},
    "return_1d": {"all", "positive", "negative", "above2", "below-2"},
    "return_1m": {"all", "positive", "negative", "above2", "below-2"},
    "volatility": {"all", "low", "moderate", "high"},
    "rsi": {"all", "oversold", "neutral", "constructive", "overbought"},
    "trend": {"all", "above-sma20", "below-sma20"},
    "valuation": {"all", "available", "missing"},
    "quality": {"all", "complete", "partial"},
    "rank": {"balanced", "momentum", "risk_adjusted", "quality"},
    "display": {"heatmap", "table", "scatter", "factors"},
}
DEFAULT_DEFINITION = {
    "universe": "bounded-us-largecap",
    "sectors": [],
    "market_cap": "all",
    "return_1d": "all",
    "return_1m": "all",
    "volatility": "all",
    "rsi": "all",
    "trend": "all",
    "valuation": "all",
    "quality": "all",
    "rank": "balanced",
    "display": "heatmap",
}


def normalize_market_screen_definition(definition: dict[str, Any] | None) -> dict[str, Any]:
    supplied = dict(definition or {})
    unknown = set(supplied) - ALLOWED_KEYS
    if unknown:
        raise ValueError(f"Unsupported saved-screen fields: {', '.join(sorted(unknown))}")
    output = dict(DEFAULT_DEFINITION)
    output.update(supplied)
    sectors = []
    if not isinstance(output.get("sectors"), list):
        raise ValueError("sectors must be a list")
    for value in output["sectors"][:12]:
        sector = str(value or "").strip()
        if not sector or not SECTOR_NAME.fullmatch(sector):
            raise ValueError("Invalid sector value")
        if sector not in sectors:
            sectors.append(sector)
    output["sectors"] = sectors
    for key, allowed in ENUMS.items():
        value = str(output.get(key) or "")
        if value not in allowed:
            raise ValueError(f"Unsupported {key}: {value}")
        output[key] = value
    return output


def _name(value: str) -> str:
    normalized = str(value or "").strip()
    if not SCREEN_NAME.fullmatch(normalized):
        raise ValueError("Screen name must be 1-80 characters and contain only letters, numbers, spaces, dot, dash, or underscore.")
    return normalized


def _screen_id(value: str) -> str:
    normalized = str(value or "").strip()
    if not SCREEN_ID.fullmatch(normalized):
        raise ValueError("Invalid screen_id.")
    return normalized


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "screen_id": row.get("screen_id"),
        "name": row.get("name"),
        "screen_version": row.get("screen_version"),
        "definition": json_loads(row.get("definition_json"), dict(DEFAULT_DEFINITION)),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "privacy_scope": "local-private",
    }


def save_market_screen(
    name: str,
    definition: dict[str, Any],
    *,
    screen_id: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    run_workspace_migrations(db_path)
    identifier = _screen_id(screen_id) if screen_id else new_id("screen")
    now = utc_now()
    row = {
        "screen_id": identifier,
        "name": _name(name),
        "screen_version": SAVED_SCREEN_VERSION,
        "definition_json": json_dumps(normalize_market_screen_definition(definition)),
        "archived": 0,
        "created_at": now,
        "updated_at": now,
    }
    execute_query(
        """
        INSERT INTO saved_market_screens (
            screen_id, name, screen_version, definition_json, archived, created_at, updated_at
        ) VALUES (
            :screen_id, :name, :screen_version, :definition_json, :archived, :created_at, :updated_at
        )
        """,
        row,
        db_path=db_path,
    )
    return _decode(row)


def list_market_screens(*, limit: int = 50, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    run_workspace_migrations(db_path)
    rows = execute_query(
        "SELECT * FROM saved_market_screens WHERE archived = 0 ORDER BY updated_at DESC, screen_id ASC LIMIT ?",
        (max(1, min(int(limit), 100)),),
        fetch=True,
        db_path=db_path,
    )
    return [_decode(row) for row in rows]  # type: ignore[arg-type]


def rename_market_screen(screen_id: str, name: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    identifier = _screen_id(screen_id)
    execute_query(
        "UPDATE saved_market_screens SET name = ?, updated_at = ? WHERE screen_id = ? AND archived = 0",
        (_name(name), utc_now(), identifier),
        db_path=db_path,
    )
    rows = execute_query(
        "SELECT * FROM saved_market_screens WHERE screen_id = ? AND archived = 0",
        (identifier,),
        fetch=True,
        one=True,
        db_path=db_path,
    )
    if not isinstance(rows, dict):
        raise ValueError("Saved screen not found.")
    return _decode(rows)


def archive_market_screen(screen_id: str, *, db_path: str | Path | None = None) -> bool:
    count = execute_query(
        "UPDATE saved_market_screens SET archived = 1, updated_at = ? WHERE screen_id = ? AND archived = 0",
        (utc_now(), _screen_id(screen_id)),
        db_path=db_path,
    )
    return bool(count)


def build_saved_screen_readiness(*, db_path: str | Path | None = None) -> dict[str, Any]:
    try:
        run_workspace_migrations(db_path)
        rows = list_market_screens(db_path=db_path)
        return {
            "store_status": "ready",
            "privacy_scope": "local-private",
            "saved_count": len(rows),
            "schema_version": SAVED_SCREEN_VERSION,
            "cloud_sync": "unavailable",
            "hosted_auth": "unavailable",
            "url_private_content_allowed": False,
            "release_private_content_allowed": False,
            "error": None,
        }
    except Exception as exc:
        return {
            "store_status": "unavailable",
            "privacy_scope": "local-private",
            "saved_count": 0,
            "schema_version": SAVED_SCREEN_VERSION,
            "cloud_sync": "unavailable",
            "hosted_auth": "unavailable",
            "url_private_content_allowed": False,
            "release_private_content_allowed": False,
            "error": type(exc).__name__,
        }
