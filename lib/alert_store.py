from __future__ import annotations

from pathlib import Path
from typing import Any

from .alert_rules import validate_alert_operator, validate_alert_scope
from .research_workspace_db import execute_query, json_dumps, json_loads, new_id, utc_now


def _decode_rule(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["active"] = bool(out.get("active"))
    out["triggered"] = bool(out.get("triggered"))
    out["metadata_json"] = json_loads(out.get("metadata_json"), {})
    return out


def _decode_event(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["triggered"] = bool(out.get("triggered"))
    out["source_snapshot_json"] = json_loads(out.get("source_snapshot_json"), {})
    out["metadata_json"] = json_loads(out.get("metadata_json"), {})
    return out


def create_alert_rule(
    *,
    watch_item_id: str = "",
    scope: str = "price",
    metric: str = "close",
    operator: str = "above",
    threshold: str | float = "",
    window: str = "",
    severity: str = "watch",
    cooldown_minutes: int = 0,
    active: bool = True,
    expires_at: str | None = None,
    metadata: dict[str, Any] | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    now = utc_now()
    row = {
        "alert_id": new_id("alert"), "watch_item_id": watch_item_id,
        "scope": validate_alert_scope(scope), "metric": metric, "operator": validate_alert_operator(operator),
        "threshold": str(threshold), "window": window, "severity": severity, "cooldown_minutes": int(cooldown_minutes),
        "active": 1 if active else 0, "triggered": 0, "expires_at": expires_at, "last_evaluated_at": None,
        "last_triggered_at": None, "created_at": now, "updated_at": now, "metadata_json": json_dumps(metadata or {}),
    }
    execute_query(
        """
        INSERT INTO alert_rules (alert_id, watch_item_id, scope, metric, operator, threshold, window, severity,
            cooldown_minutes, active, triggered, expires_at, last_evaluated_at, last_triggered_at, created_at, updated_at, metadata_json)
        VALUES (:alert_id, :watch_item_id, :scope, :metric, :operator, :threshold, :window, :severity,
            :cooldown_minutes, :active, :triggered, :expires_at, :last_evaluated_at, :last_triggered_at, :created_at, :updated_at, :metadata_json)
        """,
        row, db_path=db_path,
    )
    return get_alert_rule(row["alert_id"], db_path) or _decode_rule(row)


def get_alert_rule(alert_id: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    row = execute_query("SELECT * FROM alert_rules WHERE alert_id = ?", (alert_id,), fetch=True, one=True, db_path=db_path)
    return _decode_rule(row) if isinstance(row, dict) else None


def update_alert_rule(alert_id: str, db_path: str | Path | None = None, **updates: Any) -> dict[str, Any] | None:
    existing = get_alert_rule(alert_id, db_path)
    if not existing:
        return None
    allowed = {"watch_item_id", "scope", "metric", "operator", "threshold", "window", "severity", "cooldown_minutes", "active", "triggered", "expires_at", "last_evaluated_at", "last_triggered_at", "metadata_json"}
    row = {k: v for k, v in updates.items() if k in allowed}
    if "scope" in row: row["scope"] = validate_alert_scope(row["scope"])
    if "operator" in row: row["operator"] = validate_alert_operator(row["operator"])
    if "active" in row: row["active"] = 1 if row["active"] else 0
    if "triggered" in row: row["triggered"] = 1 if row["triggered"] else 0
    if "metadata_json" in row and not isinstance(row["metadata_json"], str): row["metadata_json"] = json_dumps(row["metadata_json"])
    row["updated_at"] = utc_now(); row["alert_id"] = alert_id
    assignments = ", ".join(f"{k} = :{k}" for k in row if k != "alert_id")
    execute_query(f"UPDATE alert_rules SET {assignments} WHERE alert_id = :alert_id", row, db_path=db_path)
    return get_alert_rule(alert_id, db_path)


def delete_alert_rule(alert_id: str, db_path: str | Path | None = None) -> bool:
    execute_query("UPDATE alert_rules SET active = 0, updated_at = ? WHERE alert_id = ?", (utc_now(), alert_id), db_path=db_path)
    return True


def list_alert_rules(active_only: bool = True, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    where = "WHERE active = 1" if active_only else ""
    rows = execute_query(f"SELECT * FROM alert_rules {where} ORDER BY updated_at DESC", fetch=True, db_path=db_path)
    return [_decode_rule(row) for row in rows]  # type: ignore[arg-type]


def store_alert_event(event: dict[str, Any], db_path: str | Path | None = None) -> dict[str, Any]:
    row = dict(event)
    row.setdefault("event_id", new_id("event")); row.setdefault("created_at", utc_now())
    row.setdefault("source_snapshot_json", json_dumps({})); row.setdefault("metadata_json", json_dumps({}))
    if not isinstance(row.get("source_snapshot_json"), str): row["source_snapshot_json"] = json_dumps(row.get("source_snapshot_json") or {})
    if not isinstance(row.get("metadata_json"), str): row["metadata_json"] = json_dumps(row.get("metadata_json") or {})
    row["triggered"] = 1 if row.get("triggered") else 0
    row.setdefault("watch_item_id", ""); row.setdefault("alert_id", ""); row.setdefault("severity", "watch")
    row.setdefault("metric", ""); row.setdefault("observed_value", ""); row.setdefault("threshold", "")
    row.setdefault("data_confidence", "unknown")
    execute_query(
        """
        INSERT INTO alert_events (event_id, alert_id, watch_item_id, status, triggered, severity, metric,
            observed_value, threshold, message, source_snapshot_json, data_confidence, created_at, metadata_json)
        VALUES (:event_id, :alert_id, :watch_item_id, :status, :triggered, :severity, :metric,
            :observed_value, :threshold, :message, :source_snapshot_json, :data_confidence, :created_at, :metadata_json)
        """,
        row, db_path=db_path,
    )
    return _decode_event(row)


def list_alert_events(limit: int = 100, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    rows = execute_query("SELECT * FROM alert_events ORDER BY created_at DESC LIMIT ?", (int(limit),), fetch=True, db_path=db_path)
    return [_decode_event(row) for row in rows]  # type: ignore[arg-type]

