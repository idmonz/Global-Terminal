from __future__ import annotations

from typing import Any


def build_shortcut_registry() -> list[dict[str, Any]]:
    return [
        {"shortcut": "OV", "command": "OVERVIEW", "label": "Overview", "workspace": "Overview", "page": "app.py", "description": "Open executive market overview."},
        {"shortcut": "WR", "command": "WAR ROOM", "label": "War Room", "workspace": "Intelligence", "page": "pages/14_War_Room.py", "description": "Open map-first event intelligence."},
        {"shortcut": "EN", "command": "CL ENERGY", "label": "Energy", "workspace": "Energy", "page": "pages/9_Energy_Geopolitics.py", "description": "Open energy and chokepoint risk."},
        {"shortcut": "CR", "command": "BTC CRYPTO", "label": "Crypto", "workspace": "Crypto", "page": "pages/8_Crypto_Intelligence.py", "description": "Open crypto stress view."},
        {"shortcut": "PV", "command": "SPY PORT", "label": "Portfolio", "workspace": "Portfolio", "page": "pages/16_Portfolio_Quant_Lab.py", "description": "Open portfolio research lab."},
        {"shortcut": "DP", "command": "DATA PROBE", "label": "Providers", "workspace": "Data", "page": "pages/17_Data_Provider_Center.py", "description": "Open provider diagnostics."},
        {"shortcut": "FT", "command": "AAPL FA", "label": "Financials", "workspace": "Financial Terminal", "page": "pages/15_Financial_Terminal.py", "description": "Open financial terminal."},
        {"shortcut": "RW", "command": "WORKSPACE", "label": "Research Workspace", "workspace": "Research", "page": "pages/19_Research_Workspace.py", "description": "Open personal research operating system."},
        {"shortcut": "WL", "command": "WATCHLIST", "label": "Watchlist", "workspace": "Research", "page": "pages/20_Watchlist_Alerts.py", "description": "Open watchlist and alert center."},
        {"shortcut": "RI", "command": "REPORTS", "label": "Report Inbox", "workspace": "Research", "page": "pages/21_Report_Inbox.py", "description": "Open report inbox."},
        {"shortcut": "SL", "command": "STRATEGY LOG", "label": "Strategy Log", "workspace": "Research", "page": "pages/22_Strategy_Decision_Log.py", "description": "Open Strategy-as-Git research log."},
        {"shortcut": "?", "command": "HELP", "label": "Help", "workspace": "Command", "page": None, "description": "Show command help."},
    ]


def find_shortcut(value: str) -> dict[str, Any] | None:
    needle = str(value or "").strip().lower()
    for item in build_shortcut_registry():
        if needle in {str(item["shortcut"]).lower(), str(item["command"]).lower(), str(item["label"]).lower()}:
            return dict(item)
    return None


def group_shortcuts_by_workspace() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in build_shortcut_registry():
        grouped.setdefault(item["workspace"], []).append(item)
    return grouped


def shortcut_to_command(value: str) -> str | None:
    item = find_shortcut(value)
    return str(item["command"]) if item else None
