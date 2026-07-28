from __future__ import annotations

from typing import Any


def build_report_action_cards(report: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rid = (report or {}).get("report_id", "")
    return [
        {"title": "Mark reviewed", "command": "MARK REPORT REVIEWED", "target_id": rid, "enabled": bool(rid), "research_only": True},
        {"title": "Flag for review", "command": "MARK REPORT REQUIRES REVIEW", "target_id": rid, "enabled": bool(rid), "research_only": True},
        {"title": "Archive report", "command": "ARCHIVE REPORT", "target_id": rid, "enabled": bool(rid), "research_only": True},
        {"title": "Export markdown", "command": "EXPORT REPORT MARKDOWN", "target_id": rid, "enabled": bool(rid), "research_only": True},
    ]
