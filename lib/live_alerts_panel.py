from __future__ import annotations

from typing import Any

from .event_severity_badges import build_event_severity_badge
from .source_freshness_strip import build_source_freshness_strip


def build_live_alerts_panel(alerts: list[dict[str, Any]] | None = None, *, source_snapshot: Any = None) -> dict[str, Any]:
    rows = []
    for alert in alerts or []:
        badge = build_event_severity_badge(alert.get("severity") or alert.get("risk"), confidence=alert.get("confidence", "unknown"), source=alert.get("source", ""))
        rows.append(
            {
                "title": alert.get("title") or alert.get("message") or "Alert condition",
                "status": alert.get("status", "pending_review"),
                "risk_label": badge["label"],
                "confidence": alert.get("confidence", "unknown"),
                "source": alert.get("source", "manual/workspace"),
                "created_at": alert.get("created_at") or alert.get("timestamp") or "",
                "caveat": badge["caveat"],
                "research_only": True,
            }
        )
    return {
        "title": "Live Alerts",
        "rows": rows,
        "empty": len(rows) == 0,
        "empty_message": "No supplied alert context. Manual evaluation only.",
        "source_freshness": build_source_freshness_strip(source_snapshot or [{"source": "alert_panel", "freshness": "unavailable"}], title="Alert panel source freshness"),
        "no_fake_live_data": True,
        "research_only": True,
    }
