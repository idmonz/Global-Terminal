from __future__ import annotations
from typing import Any

from .research_command_safety import build_blocked_research_boundary_card, detect_forbidden_command_intent

RESEARCH_COMMANDS = [
    {"code": "WORKSPACE", "page": "pages/19_Research_Workspace.py", "label": "Research Workspace"},
    {"code": "WATCHLIST", "page": "pages/20_Watchlist_Alerts.py", "label": "Watchlist & Alerts"},
    {"code": "ADD WATCHLIST", "page": "pages/20_Watchlist_Alerts.py", "label": "Add Watchlist Item"},
    {"code": "ALERTS", "page": "pages/20_Watchlist_Alerts.py", "label": "Alert Center"},
    {"code": "EVALUATE ALERTS", "page": "pages/20_Watchlist_Alerts.py", "label": "Evaluate Alerts"},
    {"code": "REPORTS", "page": "pages/21_Report_Inbox.py", "label": "Report Inbox"},
    {"code": "GENERATE WATCHLIST BRIEF", "page": "pages/21_Report_Inbox.py", "label": "Generate Watchlist Brief"},
    {"code": "GENERATE PROVIDER REPORT", "page": "pages/21_Report_Inbox.py", "label": "Generate Provider Health Report"},
    {"code": "GENERATE WAR ROOM BRIEF", "page": "pages/21_Report_Inbox.py", "label": "Generate War Room Brief"},
    {"code": "GENERATE STRATEGY REVIEW", "page": "pages/21_Report_Inbox.py", "label": "Generate Strategy Review"},
    {"code": "STRATEGY LOG", "page": "pages/22_Strategy_Decision_Log.py", "label": "Strategy Decision Log"},
    {"code": "COMMIT STRATEGY", "page": "pages/22_Strategy_Decision_Log.py", "label": "Create Strategy Commit"},
    {"code": "PROVIDER REPORT", "page": "pages/21_Report_Inbox.py", "label": "Provider Report"},
    {"code": "DATA QUALITY REPORT", "page": "pages/21_Report_Inbox.py", "label": "Data Quality Report"},
    {"code": "TOOL CENTER", "page": "pages/23_Research_Tool_Center.py", "label": "Research Tool Center"},

    {"code": "OPTIONS LAB", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Options Pricing & Quant Model Lab"},
    {"code": "PRICE OPTION", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Price Option"},
    {"code": "SOLVE IV", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Solve Implied Volatility"},
    {"code": "PAYOFF SCENARIO", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Build Payoff Scenario"},
    {"code": "OPTIONS REPORT", "page": "pages/21_Report_Inbox.py", "label": "Generate Options Report"},
    {"code": "MODEL SNAPSHOT", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Create Quant Model Snapshot"},

    {"code": "OPTION CHAIN", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Import Option Chain CSV"},
    {"code": "VOL SURFACE", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Build Vol Surface Snapshot"},
    {"code": "OPTION BOOK", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Build Option Book Risk Snapshot"},
    {"code": "OPTIONS CHAIN REPORT", "page": "pages/21_Report_Inbox.py", "label": "Generate Options Chain Report"},
    {"code": "SURFACE REPORT", "page": "pages/21_Report_Inbox.py", "label": "Generate Vol Surface Report"},
    {"code": "OPTION BOOK REPORT", "page": "pages/21_Report_Inbox.py", "label": "Generate Option Book Risk Report"},
    {"code": "QUANT DIAGNOSTICS", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Run Local Quant Diagnostics"},
    {"code": "ATTACH MODEL RESULT", "page": "pages/21_Report_Inbox.py", "label": "Attach Model Snapshot"},
    {"code": "OPTIONS CASE", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Create Options Research Case"},
    {"code": "SURFACE REVIEW", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Create Surface QA Review Item"},
    {"code": "SAVE OPTION CASE", "page": "pages/24_Options_Quant_Model_Lab.py", "label": "Save Options Case Artifact"},
]


def build_research_command_palette() -> list[dict[str, Any]]:
    return [dict(c, research_only=True) for c in RESEARCH_COMMANDS]


def search_research_commands(query: str = "") -> list[dict[str, Any]]:
    needle = str(query or "").upper()
    rows = build_research_command_palette()
    return rows if not needle else [r for r in rows if needle in r["code"] or needle in r["label"].upper()]


def route_research_command(command: str) -> dict[str, Any]:
    safety = detect_forbidden_command_intent(command)
    normalized = " ".join(str(command or "").upper().split())
    if safety.get("blocked"):
        card = build_blocked_research_boundary_card(command)
        return {"ok": False, "status": "blocked", "command": normalized, "blocked_card": card, "suggestions": card["safe_alternatives"], "research_only": True}
    for row in build_research_command_palette():
        if normalized == row["code"] or (normalized.endswith(" WATCH") and row["code"] == "WATCHLIST"):
            return {"ok": True, "status": "routed", "command": normalized, **row}
    return {"ok": False, "status": "not_found", "command": normalized, "suggestions": search_research_commands(normalized[:10]), "research_only": True}



from .command_palette_suggestions import build_quick_add_payload, search_research_objects, suggest_actions_for_query
from .command_palette_ui import build_command_palette_state, build_command_result_card
from .research_object_resolver import resolve_research_object
