from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from .research_workspace_schema import SCHEMA_VERSION, get_schema_sql
from .research_workspace_paths import get_workspace_db_path, ensure_private_workspace_dirs


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {str(row[1]) for row in rows}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _run_incremental_migrations(conn: sqlite3.Connection) -> None:
    _ensure_column(conn, "watchlist_items", "watchlist_id", "TEXT NOT NULL DEFAULT 'primary'")
    _ensure_column(conn, "watchlist_items", "position", "INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_watchlist_items_list_position "
        "ON watchlist_items(watchlist_id, active, position, updated_at DESC)"
    )
    _ensure_column(conn, "report_inbox_items", "report_review_status", "TEXT DEFAULT 'unread'")
    _ensure_column(conn, "report_inbox_items", "reviewed_at", "TEXT")
    _ensure_column(conn, "report_inbox_items", "review_notes", "TEXT DEFAULT ''")
    _ensure_column(conn, "strategy_commits", "review_status", "TEXT DEFAULT 'requires_review'")
    _ensure_column(conn, "strategy_commits", "reviewed_at", "TEXT")
    _ensure_column(conn, "strategy_commits", "review_notes", "TEXT DEFAULT ''")


def run_workspace_migrations(db_path: str | Path | None = None) -> Path:
    resolved = get_workspace_db_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    if db_path is None:
        ensure_private_workspace_dirs()
    with closing(sqlite3.connect(resolved)) as conn:
        for statement in get_schema_sql():
            conn.execute(statement)
        _run_incremental_migrations(conn)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    return resolved


def get_workspace_schema_version(db_path: str | Path | None = None) -> int:
    resolved = get_workspace_db_path(db_path)
    if not resolved.exists():
        return 0
    with closing(sqlite3.connect(resolved)) as conn:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])
