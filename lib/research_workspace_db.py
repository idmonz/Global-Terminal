from __future__ import annotations

import json
import shutil
import sqlite3
import threading
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .research_workspace_migrations import run_workspace_migrations
from .research_workspace_paths import get_workspace_db_path, ensure_private_workspace_dirs
from .research_workspace_schema import SCHEMA_VERSION, TABLE_NAMES


_INITIALIZED_DB_PATHS: set[tuple[str, int]] = set()
_INITIALIZED_DB_LOCK = threading.Lock()


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool | None:
        try:
            return super().__exit__(exc_type, exc, traceback)
        finally:
            self.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)


def json_loads(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def initialize_workspace_db(db_path: str | Path | None = None) -> Path:
    if db_path is None:
        ensure_private_workspace_dirs()
    resolved = get_workspace_db_path(db_path).resolve()
    key = (str(resolved), SCHEMA_VERSION)
    if resolved.exists() and key in _INITIALIZED_DB_PATHS:
        return resolved
    with _INITIALIZED_DB_LOCK:
        if resolved.exists() and key in _INITIALIZED_DB_PATHS:
            return resolved
        migrated = run_workspace_migrations(resolved)
        _INITIALIZED_DB_PATHS.add(key)
        return migrated


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    resolved = initialize_workspace_db(db_path)
    conn = sqlite3.connect(resolved, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    return dict(row)


def execute_query(
    query: str,
    params: Iterable[Any] | dict[str, Any] | None = None,
    *,
    fetch: bool = False,
    one: bool = False,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]] | dict[str, Any] | int | None:
    with closing(get_connection(db_path)) as conn:
        cur = conn.execute(query, params or [])
        if fetch:
            if one:
                row = cur.fetchone()
                return row_to_dict(row) if row else None
            return [row_to_dict(row) for row in cur.fetchall()]
        conn.commit()
        return cur.rowcount


def backup_workspace_db(destination: str | Path | None = None, db_path: str | Path | None = None) -> Path:
    source = initialize_workspace_db(db_path)
    target = Path(destination) if destination else source.with_suffix(f".{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.backup.db")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def export_workspace_json(db_path: str | Path | None = None) -> dict[str, Any]:
    initialize_workspace_db(db_path)
    payload: dict[str, Any] = {"exported_at": utc_now(), "schema_tables": TABLE_NAMES, "tables": {}}
    with closing(get_connection(db_path)) as conn:
        for table in TABLE_NAMES:
            rows = [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]
            payload["tables"][table] = rows
    return payload


def import_workspace_json(payload: dict[str, Any], db_path: str | Path | None = None, *, replace: bool = False) -> dict[str, Any]:
    initialize_workspace_db(db_path)
    imported: dict[str, int] = {}
    tables = dict((payload or {}).get("tables") or {})
    with closing(get_connection(db_path)) as conn:
        for table, rows in tables.items():
            if table not in TABLE_NAMES:
                continue
            if replace:
                conn.execute(f"DELETE FROM {table}")
            count = 0
            for row in rows or []:
                keys = list(row.keys())
                placeholders = ", ".join([":" + key for key in keys])
                columns = ", ".join(keys)
                conn.execute(f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})", row)
                count += 1
            imported[table] = count
        conn.commit()
    return {"imported": imported, "replaced": replace}


def reset_demo_workspace_data(db_path: str | Path | None = None) -> dict[str, Any]:
    initialize_workspace_db(db_path)
    now = utc_now()
    with closing(get_connection(db_path)) as conn:
        for table in TABLE_NAMES:
            conn.execute(f"DELETE FROM {table}")
        conn.execute(
            """
            INSERT INTO workspace_profile (
                profile_id, display_name, base_currency, default_region, preferred_asset_classes,
                preferred_time_horizon, risk_tolerance_label, default_workspace, enabled_desks,
                report_preferences, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "demo_profile",
                "Demo Researcher",
                "USD",
                "Global",
                json_dumps(["equity", "crypto", "commodity", "osint"]),
                "daily + swing research",
                "research-only",
                "Research Workspace",
                json_dumps(["War Room", "Energy", "Crypto", "Portfolio"]),
                json_dumps({"briefing": "manual"}),
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO watchlist_items (
                item_id, item_type, symbol, display_name, asset_class, exchange, region, country,
                tags, watch_reason, default_command, default_page, source, active, created_at, updated_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "demo_watch_btc",
                "crypto",
                "BTCUSDT",
                "Bitcoin perpetual proxy",
                "crypto",
                "Binance",
                "Global",
                "",
                json_dumps(["demo", "crypto_derivatives"]),
                "Demo item for funding and volatility monitoring.",
                "BTCUSDT WATCH",
                "pages/20_Watchlist_Alerts.py",
                "demo",
                1,
                now,
                now,
                json_dumps({"demo": True}),
            ),
        )
        conn.commit()
    return {"status": "reset", "demo": True, "db_path": str(get_workspace_db_path(db_path))}
