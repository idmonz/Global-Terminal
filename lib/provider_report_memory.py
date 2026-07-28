from __future__ import annotations
from pathlib import Path
from typing import Any
from .provider_snapshot_store import list_provider_health_snapshots, get_latest_provider_health_snapshot
from .data_quality_snapshot_store import list_data_quality_snapshots, get_latest_data_quality_snapshot

BAD_STATES = {"missing_key", "missing-key", "error", "stale", "unavailable", "historical_only", "proxy"}


def build_provider_report_memory(db_path: str | Path | None = None, provider_name: str | None = None) -> dict[str, Any]:
    rows = list_provider_health_snapshots(provider_name, limit=100, db_path=db_path)
    latest = rows[0] if rows else None
    gaps = [r for r in rows if str(r.get("status") or "").lower() in BAD_STATES or r.get("missing_keys")]
    return {"latest": latest, "snapshots": rows, "snapshot_count": len(rows), "gap_count": len(gaps), "gaps": gaps, "status": (latest or {}).get("status", "unavailable")}


def build_data_quality_report_memory(db_path: str | Path | None = None, scope: str | None = None) -> dict[str, Any]:
    rows = list_data_quality_snapshots(scope, limit=100, db_path=db_path)
    latest = rows[0] if rows else None
    gaps = [r for r in rows if str(r.get("status") or "").lower() in BAD_STATES or r.get("gaps_json")]
    return {"latest": latest, "snapshots": rows, "snapshot_count": len(rows), "gap_count": len(gaps), "gaps": gaps, "status": (latest or {}).get("status", "unavailable")}
