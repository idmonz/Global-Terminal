from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .research_workspace_db import export_workspace_json, import_workspace_json, utc_now
from .research_workspace_paths import get_private_watchlist_export_dir


def export_workspace_json_file(path: str | Path | None = None, db_path: str | Path | None = None) -> Path:
    payload = export_workspace_json(db_path)
    target = Path(path) if path else get_private_watchlist_export_dir() / f"research_workspace_export_{utc_now().replace(':', '').replace('+', 'Z')}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def import_workspace_json_file(path: str | Path, db_path: str | Path | None = None, *, replace: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return import_workspace_json(payload, db_path, replace=replace)

