from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DATA_DIR = ROOT / "data" / "private"
REPORTS_DIR = PRIVATE_DATA_DIR / "reports"
STRATEGY_COMMITS_DIR = PRIVATE_DATA_DIR / "strategy_commits"
WATCHLIST_EXPORTS_DIR = PRIVATE_DATA_DIR / "watchlist_exports"
DEFAULT_DB_PATH = PRIVATE_DATA_DIR / "research_workspace.db"

PRIVATE_SUBDIRS = [PRIVATE_DATA_DIR, REPORTS_DIR, STRATEGY_COMMITS_DIR, WATCHLIST_EXPORTS_DIR]


def ensure_private_workspace_dirs() -> list[Path]:
    for directory in PRIVATE_SUBDIRS:
        directory.mkdir(parents=True, exist_ok=True)
    return list(PRIVATE_SUBDIRS)


def _coerce_path(path: str | Path | None = None) -> Path:
    if path is None:
        override = os.getenv("RESEARCH_WORKSPACE_DB_PATH")
        return Path(override).expanduser() if override else DEFAULT_DB_PATH
    return Path(path).expanduser()


def get_workspace_db_path(path: str | Path | None = None) -> Path:
    db_path = _coerce_path(path)
    if not db_path.is_absolute():
        db_path = ROOT / db_path
    return db_path.resolve()


def get_private_report_dir() -> Path:
    return REPORTS_DIR


def get_private_strategy_commit_dir() -> Path:
    return STRATEGY_COMMITS_DIR


def get_private_watchlist_export_dir() -> Path:
    return WATCHLIST_EXPORTS_DIR


def is_private_workspace_path(path: str | Path) -> bool:
    target = Path(path).resolve()
    private = PRIVATE_DATA_DIR.resolve()
    try:
        target.relative_to(private)
        return True
    except ValueError:
        return False

