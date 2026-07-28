from __future__ import annotations

from collections import defaultdict
from typing import Any

from .event_severity_badges import build_event_risk_label

_RISK_SCORE = {"LOW": 1, "ELEVATED": 2, "HIGH": 3, "CRITICAL": 4}


def build_hotspot_panel(events: list[dict[str, Any]] | None = None, *, limit: int = 10) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {"event_count": 0, "score": 0, "risk_labels": set(), "sources": set()})
    for event in events or []:
        region = event.get("region") or event.get("location") or event.get("country") or "Unspecified"
        risk = build_event_risk_label(event.get("severity") or event.get("risk"), confidence=event.get("confidence", "unknown"))
        bucket = buckets[str(region)]
        bucket["event_count"] += 1
        bucket["score"] += _RISK_SCORE.get(risk, 1)
        bucket["risk_labels"].add(risk)
        bucket["sources"].add(event.get("source") or "unknown")
    rows = []
    for region, bucket in buckets.items():
        top_label = max(bucket["risk_labels"], key=lambda label: _RISK_SCORE.get(label, 0)) if bucket["risk_labels"] else "LOW"
        rows.append({"region": region, "event_count": bucket["event_count"], "score": bucket["score"], "risk_label": top_label, "sources": sorted(bucket["sources"]), "research_only": True})
    rows.sort(key=lambda row: (row["score"], row["event_count"]), reverse=True)
    return {"title": "Hotspots", "rows": rows[:limit], "empty": not rows, "no_fake_live_data": True, "research_only": True}
