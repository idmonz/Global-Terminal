from __future__ import annotations

from typing import Any

from .provider_caveat_panel import build_provider_caveat_panel
from .source_freshness_strip import build_source_freshness_strip


def build_report_source_caveat_panel(report: dict[str, Any] | None = None) -> dict[str, Any]:
    report = report or {}
    gaps = report.get("provider_gaps_json") or []
    providers = []
    for gap in gaps:
        providers.append({"provider_id": str(gap), "status": "unavailable", "confidence": "unknown", "caveat": str(gap)})
    return {
        "title": "Report source caveats",
        "freshness": build_source_freshness_strip(report.get("source_snapshot_json", {}), title="Report source freshness"),
        "provider_caveats": build_provider_caveat_panel(providers),
        "gaps": gaps,
        "research_only": True,
    }
