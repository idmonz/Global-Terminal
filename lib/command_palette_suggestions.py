from __future__ import annotations

from typing import Any

from .research_command_safety import build_blocked_research_boundary_card, detect_forbidden_command_intent, sanitize_research_query
from .research_object_resolver import resolve_research_object


_ACTIONS_BY_TYPE = {
    "asset": [
        ("Open Financial Terminal", "FINANCIAL TERMINAL", "pages/15_Financial_Terminal.py"),
        ("Add Watchlist", "ADD WATCHLIST", "pages/20_Watchlist_Alerts.py"),
        ("Create Price Alert", "CREATE PRICE ALERT", "pages/20_Watchlist_Alerts.py"),
        ("Generate Asset Brief", "GENERATE ASSET BRIEF", "pages/21_Report_Inbox.py"),
    ],
    "crypto": [
        ("Open Crypto Intelligence", "CRYPTO INTELLIGENCE", "pages/8_Crypto_Intelligence.py"),
        ("Add Crypto Watch", "ADD WATCHLIST", "pages/20_Watchlist_Alerts.py"),
        ("Create Funding/OI Alert", "CREATE DERIVATIVES ALERT", "pages/20_Watchlist_Alerts.py"),
        ("Generate Crypto Watch", "GENERATE WATCHLIST BRIEF", "pages/21_Report_Inbox.py"),
    ],
    "region": [
        ("Open War Room", "GLOBAL WAR", "pages/14_War_Room.py"),
        ("Add Chokepoint Watch", "ADD WATCHLIST", "pages/20_Watchlist_Alerts.py"),
        ("Generate Energy Brief", "GENERATE ENERGY BRIEF", "pages/21_Report_Inbox.py"),
    ],
    "provider": [
        ("Open Provider Center", "DATA PROBE", "pages/17_Data_Provider_Center.py"),
        ("Add Provider Watch", "ADD WATCHLIST", "pages/20_Watchlist_Alerts.py"),
        ("Generate Provider Report", "GENERATE PROVIDER REPORT", "pages/21_Report_Inbox.py"),
    ],
    "strategy": [
        ("Open Strategy Log", "STRATEGY LOG", "pages/22_Strategy_Decision_Log.py"),
        ("Add Strategy Watch", "ADD WATCHLIST", "pages/20_Watchlist_Alerts.py"),
        ("Create Commit", "COMMIT STRATEGY", "pages/22_Strategy_Decision_Log.py"),
        ("Generate Strategy Review", "GENERATE STRATEGY REVIEW", "pages/21_Report_Inbox.py"),
    ],
    "options": [
        ("Open Options Lab", "OPTIONS LAB", "pages/24_Options_Quant_Model_Lab.py"),
        ("Price Option", "PRICE OPTION", "pages/24_Options_Quant_Model_Lab.py"),
        ("Solve Implied Volatility", "SOLVE IV", "pages/24_Options_Quant_Model_Lab.py"),
        ("Build Payoff Scenario", "PAYOFF SCENARIO", "pages/24_Options_Quant_Model_Lab.py"),
        ("Import Option Chain CSV", "OPTION CHAIN", "pages/24_Options_Quant_Model_Lab.py"),
        ("Build Vol Surface Snapshot", "VOL SURFACE", "pages/24_Options_Quant_Model_Lab.py"),
        ("Build Option Book Risk Snapshot", "OPTION BOOK", "pages/24_Options_Quant_Model_Lab.py"),
        ("Run Local Quant Diagnostics", "QUANT DIAGNOSTICS", "pages/24_Options_Quant_Model_Lab.py"),
        ("Search Options Cases", "SEARCH OPTIONS CASES", "pages/24_Options_Quant_Model_Lab.py"),
        ("Surface Review Queue", "SURFACE REVIEW QUEUE", "pages/24_Options_Quant_Model_Lab.py"),
    ],
    "topic": [
        ("Open Research Workspace", "WORKSPACE", "pages/19_Research_Workspace.py"),
        ("Add Watchlist", "ADD WATCHLIST", "pages/20_Watchlist_Alerts.py"),
        ("Generate Watchlist Brief", "GENERATE WATCHLIST BRIEF", "pages/21_Report_Inbox.py"),
    ],
}


def is_blocked_command_query(query: str) -> bool:
    return bool(detect_forbidden_command_intent(query).get("blocked"))


def suggest_actions_for_query(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    if is_blocked_command_query(query):
        card = build_blocked_research_boundary_card(query)
        return [
            {
                "label": card["title"],
                "command": "BLOCKED_RESEARCH_BOUNDARY",
                "page": "",
                "reason": card["message"],
                "safe_alternatives": card["safe_alternatives"],
                "matched": card["matched"],
                "enabled": False,
                "research_only": True,
            }
        ]
    obj = resolve_research_object(query)
    if any(token in str(query or "").lower() for token in ["option", "greeks", "implied vol", "payoff", "black scholes", "black-76", "vol surface", "option chain", "option book", "quant diagnostics", "options case", "surface review"]):
        obj = {**obj, "object_type": "options", "display_name": obj.get("display_name") or query}
    rows = _ACTIONS_BY_TYPE.get(obj["object_type"], _ACTIONS_BY_TYPE["topic"])
    suggestions = []
    for label, command, page in rows[:limit]:
        suggestions.append(
            {
                "label": label,
                "command": command,
                "page": page,
                "object_type": obj["object_type"],
                "object": obj.get("display_name", query),
                "confidence": obj.get("confidence", "unknown"),
                "enabled": True,
                "research_only": True,
            }
        )
    return suggestions


def build_quick_add_payload(query: str) -> dict[str, Any]:
    if is_blocked_command_query(query):
        return {}
    obj = resolve_research_object(query)
    item_type = {"asset": "equity", "crypto": "crypto", "region": "region", "provider": "provider", "strategy": "strategy"}.get(obj["object_type"], "topic")
    return {
        "display_name": obj.get("display_name", query),
        "symbol": obj.get("normalized", query) if obj["object_type"] in {"asset", "crypto", "provider"} else "",
        "item_type": item_type,
        "watch_reason": "Added from command palette for research monitoring.",
        "tags": ["command_palette", obj["object_type"]],
        "research_only": True,
    }


def search_research_objects(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    obj = resolve_research_object(query)
    actions = suggest_actions_for_query(query, limit=limit)
    return [{**obj, "actions": actions, "rank": 1}]
