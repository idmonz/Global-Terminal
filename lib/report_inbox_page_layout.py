from __future__ import annotations
from pathlib import Path
from typing import Any
from .report_inbox import list_reports
from .report_visuals import build_report_cards, build_report_timeline
from .headless_report_runner import REPORT_GENERATORS
from .report_filter_engine import build_report_filter_state
from .report_sidebar import build_report_sidebar
from .report_reader_panel import build_report_reader_panel
from .report_action_cards import build_report_action_cards
from .report_review_workflow import build_report_review_workflow
from .report_source_caveat_panel import build_report_source_caveat_panel


def build_report_inbox_page_payload(db_path: str | Path | None = None, query: str = "", report_type: str | None = None, review_status: str | None = None) -> dict[str, Any]:
    reports = list_reports(db_path=db_path)
    filter_state = build_report_filter_state(reports, query=query, report_type=report_type, review_status=review_status)
    visible_reports = filter_state["filtered_reports"]
    latest = visible_reports[0] if visible_reports else (reports[0] if reports else None)
    return {
        "generators": sorted(REPORT_GENERATORS.keys()),
        "reports": reports,
        "visible_reports": visible_reports,
        "filter_state": filter_state,
        "sidebar": build_report_sidebar(visible_reports, selected_report_id=(latest or {}).get("report_id")),
        "reader_panel": build_report_reader_panel(latest),
        "action_cards": build_report_action_cards(latest),
        "review_workflow": build_report_review_workflow(latest),
        "source_caveat_panel": build_report_source_caveat_panel(latest),
        "cards": build_report_cards(visible_reports),
        "timeline": build_report_timeline(visible_reports),
        "latest": latest,
        "source_snapshot": (latest or {}).get("source_snapshot_json", {}),
        "provider_gaps": (latest or {}).get("provider_gaps_json", []),
        "empty_states": {"no_reports": len(reports) == 0, "no_visible_reports": len(visible_reports) == 0},
        "raw_payload_available": True,
        "research_only": True,
    }
