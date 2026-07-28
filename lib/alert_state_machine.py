from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Any
from .research_workspace_db import execute_query, utc_now, json_loads, json_dumps


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def apply_alert_expiry(rule: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    expires = parse_dt(rule.get("expires_at"))
    if expires and expires < now:
        return {"expired": True, "status": "skipped_expired", "message": "Alert rule expired; evaluation skipped."}
    return {"expired": False}


def apply_alert_cooldown(rule: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    cooldown = int(rule.get("cooldown_minutes") or 0)
    last = parse_dt(rule.get("last_triggered_at"))
    if cooldown > 0 and last and last + timedelta(minutes=cooldown) > now:
        return {"in_cooldown": True, "status": "skipped_cooldown", "cooldown_minutes": cooldown, "message": "Alert rule is inside cooldown window."}
    return {"in_cooldown": False, "cooldown_minutes": cooldown}


def get_previous_observed_value(alert_id: str, metric: str | None = None, db_path=None) -> Any:
    row = execute_query("SELECT metadata_json, observed_value FROM alert_events WHERE alert_id = ? ORDER BY created_at DESC LIMIT 1", (alert_id,), fetch=True, one=True, db_path=db_path)
    if not isinstance(row, dict):
        return None
    meta = json_loads(row.get("metadata_json"), {})
    return meta.get("observed_value_raw", row.get("observed_value"))


def classify_alert_transition(previous_triggered: bool | None, triggered: bool, status: str) -> str:
    if status.startswith("skipped"):
        return status
    if triggered and not previous_triggered:
        return "new_trigger"
    if triggered and previous_triggered:
        return "still_triggered"
    if not triggered and previous_triggered:
        return "resolved"
    return "unchanged"


def update_alert_state(rule: dict[str, Any], evaluation: dict[str, Any], *, db_path=None) -> None:
    now = utc_now()
    last_triggered = now if evaluation.get("triggered") else rule.get("last_triggered_at")
    execute_query("UPDATE alert_rules SET triggered=?, last_evaluated_at=?, last_triggered_at=?, updated_at=? WHERE alert_id=?", (1 if evaluation.get("triggered") else 0, now, last_triggered, now, rule.get("alert_id")), db_path=db_path)
