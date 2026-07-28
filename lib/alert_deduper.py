from __future__ import annotations
from typing import Any
from .research_workspace_db import execute_query


def build_alert_event_hash(rule: dict[str, Any], evaluation: dict[str, Any]) -> str:
    return "|".join(str(x) for x in [rule.get("alert_id"), rule.get("watch_item_id"), rule.get("metric"), rule.get("operator"), rule.get("threshold"), evaluation.get("status"), evaluation.get("observed_value")])


def dedupe_alert_event(rule: dict[str, Any], evaluation: dict[str, Any], *, db_path=None) -> dict[str, Any]:
    key = build_alert_event_hash(rule, evaluation)
    row = execute_query("SELECT event_id FROM alert_events WHERE metadata_json LIKE ? ORDER BY created_at DESC LIMIT 1", (f'%"event_hash": "{key}"%',), fetch=True, one=True, db_path=db_path)
    return {"dedupe_key": key, "duplicate": bool(row), "existing_event_id": (row or {}).get("event_id") if isinstance(row, dict) else None}
