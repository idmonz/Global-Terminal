from __future__ import annotations

from pathlib import Path
from typing import Any

from .research_workspace_db import execute_query, json_dumps, json_loads, utc_now

DEFAULT_PROFILE_ID = "default"


def _decode_profile(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    decoded = dict(row)
    decoded["preferred_asset_classes"] = json_loads(decoded.get("preferred_asset_classes"), [])
    decoded["enabled_desks"] = json_loads(decoded.get("enabled_desks"), [])
    decoded["report_preferences"] = json_loads(decoded.get("report_preferences"), {})
    return decoded


def build_default_workspace_profile(**overrides: Any) -> dict[str, Any]:
    now = utc_now()
    profile = {
        "profile_id": DEFAULT_PROFILE_ID,
        "display_name": "Personal Research Workspace",
        "base_currency": "USD",
        "default_region": "Global",
        "preferred_asset_classes": ["equity", "crypto", "commodity", "fx", "rates", "osint"],
        "preferred_time_horizon": "daily / weekly research",
        "risk_tolerance_label": "research-only",
        "default_workspace": "Research Workspace",
        "enabled_desks": ["War Room", "Energy", "Crypto", "Portfolio", "Provider Center"],
        "report_preferences": {"manual_generation": True, "email_auto_send": False},
        "created_at": now,
        "updated_at": now,
    }
    profile.update(overrides)
    return profile


def save_workspace_profile(profile: dict[str, Any], db_path: str | Path | None = None) -> dict[str, Any]:
    now = utc_now()
    payload = build_default_workspace_profile(**profile)
    payload["updated_at"] = now
    payload["preferred_asset_classes"] = json_dumps(payload.get("preferred_asset_classes") or [])
    payload["enabled_desks"] = json_dumps(payload.get("enabled_desks") or [])
    payload["report_preferences"] = json_dumps(payload.get("report_preferences") or {})
    execute_query(
        """
        INSERT OR REPLACE INTO workspace_profile (
            profile_id, display_name, base_currency, default_region, preferred_asset_classes,
            preferred_time_horizon, risk_tolerance_label, default_workspace, enabled_desks,
            report_preferences, created_at, updated_at
        ) VALUES (:profile_id, :display_name, :base_currency, :default_region, :preferred_asset_classes,
            :preferred_time_horizon, :risk_tolerance_label, :default_workspace, :enabled_desks,
            :report_preferences, :created_at, :updated_at)
        """,
        payload,
        db_path=db_path,
    )
    return load_workspace_profile(payload["profile_id"], db_path) or profile


def load_workspace_profile(profile_id: str = DEFAULT_PROFILE_ID, db_path: str | Path | None = None) -> dict[str, Any] | None:
    row = execute_query("SELECT * FROM workspace_profile WHERE profile_id = ?", (profile_id,), fetch=True, one=True, db_path=db_path)
    return _decode_profile(row if isinstance(row, dict) else None)


def get_or_create_workspace_profile(db_path: str | Path | None = None) -> dict[str, Any]:
    existing = load_workspace_profile(DEFAULT_PROFILE_ID, db_path)
    if existing:
        return existing
    return save_workspace_profile(build_default_workspace_profile(), db_path)

