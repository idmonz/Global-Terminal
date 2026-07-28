from __future__ import annotations
from typing import Any

FORBIDDEN_ACTION_PHRASES = ["should " + "buy", "should " + "sell", "go " + "long", "go " + "short", "time to " + "enter", "time to " + "exit", "trade " + "now"]


def scan_report_text(text: str) -> dict[str, Any]:
    lower = (text or "").lower()
    hits = [p for p in FORBIDDEN_ACTION_PHRASES if p in lower]
    return {"passed": not hits, "hits": hits, "research_only": True}


def build_report_quality_summary(context: dict[str, Any]) -> dict[str, Any]:
    provider_gaps = context.get("provider_gaps") or []
    return {"provider_gap_count": len(provider_gaps), "has_source_snapshot": bool(context.get("source_snapshot")), "research_only": True}
