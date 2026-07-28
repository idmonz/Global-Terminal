from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


FUNCTIONS: list[dict[str, Any]] = [
    {"code": "CC", "label": "Command Center", "page": "app.py", "category": "workspace", "pattern": "single"},
    {"code": "HELP", "label": "Function Directory", "page": "app.py", "category": "help", "pattern": "single"},
    {"code": "DATA PROBE", "label": "Provider Center", "page": "pages/17_Data_Provider_Center.py", "category": "data", "pattern": "phrase"},
    {"code": "OPENBB HUB", "label": "OpenBB Data Hub", "page": "pages/18_OpenBB_Data_Hub.py", "category": "data", "pattern": "phrase"},
    {"code": "GLOBAL WAR", "label": "War Room", "page": "pages/14_War_Room.py", "category": "osint", "pattern": "phrase"},
    {"code": "BTC CRYPTO", "label": "Crypto Intelligence", "page": "pages/8_Crypto_Intelligence.py", "category": "crypto", "pattern": "asset_desk"},
    {"code": "CL ENERGY", "label": "Energy / Geopolitics", "page": "pages/9_Energy_Geopolitics.py", "category": "energy", "pattern": "asset_desk"},
    {"code": "AAPL FA", "label": "Financial Analysis", "page": "pages/15_Financial_Terminal.py", "category": "financials", "pattern": "ticker_function"},
    {"code": "AAPL KEY", "label": "Key Ratios", "page": "pages/15_Financial_Terminal.py", "category": "financials", "pattern": "ticker_function"},
    {"code": "AAPL FIL", "label": "Filings", "page": "pages/15_Financial_Terminal.py", "category": "financials", "pattern": "ticker_function"},
    {"code": "AAPL OMON", "label": "Options Monitor", "page": "pages/15_Financial_Terminal.py", "category": "options", "pattern": "ticker_function"},
    {"code": "SPY PORT", "label": "Portfolio Lab", "page": "pages/16_Portfolio_Quant_Lab.py", "category": "portfolio", "pattern": "ticker_function"},
    {"code": "STRAT WORKBENCH", "label": "Alpha Strategy Workbench", "page": "pages/16_Portfolio_Quant_Lab.py", "category": "strategy", "pattern": "phrase"},
    {"code": "RISK LAB", "label": "Risk / Scenario Lab", "page": "pages/11_Risk_Lab.py", "category": "risk", "pattern": "phrase"},

    {"code": "WORKSPACE", "label": "Research Workspace", "page": "pages/19_Research_Workspace.py", "category": "research", "pattern": "single"},
    {"code": "WATCHLIST", "label": "Watchlist & Alerts", "page": "pages/20_Watchlist_Alerts.py", "category": "research", "pattern": "single"},
    {"code": "ADD WATCHLIST", "label": "Add Watchlist Item", "page": "pages/20_Watchlist_Alerts.py", "category": "research", "pattern": "phrase"},
    {"code": "ALERTS", "label": "Alert Center", "page": "pages/20_Watchlist_Alerts.py", "category": "research", "pattern": "single"},
    {"code": "EVALUATE ALERTS", "label": "Evaluate Alerts", "page": "pages/20_Watchlist_Alerts.py", "category": "research", "pattern": "phrase"},
    {"code": "REPORTS", "label": "Report Inbox", "page": "pages/21_Report_Inbox.py", "category": "research", "pattern": "single"},
    {"code": "GENERATE WATCHLIST BRIEF", "label": "Generate Watchlist Brief", "page": "pages/21_Report_Inbox.py", "category": "research", "pattern": "phrase"},
    {"code": "GENERATE PROVIDER REPORT", "label": "Generate Provider Health Report", "page": "pages/21_Report_Inbox.py", "category": "research", "pattern": "phrase"},
    {"code": "GENERATE WAR ROOM BRIEF", "label": "Generate War Room Brief", "page": "pages/21_Report_Inbox.py", "category": "research", "pattern": "phrase"},
    {"code": "GENERATE STRATEGY REVIEW", "label": "Generate Strategy Review", "page": "pages/21_Report_Inbox.py", "category": "research", "pattern": "phrase"},
    {"code": "STRATEGY LOG", "label": "Strategy Decision Log", "page": "pages/22_Strategy_Decision_Log.py", "category": "research", "pattern": "phrase"},
    {"code": "COMMIT STRATEGY", "label": "Create Strategy Commit", "page": "pages/22_Strategy_Decision_Log.py", "category": "research", "pattern": "phrase"},
    {"code": "PROVIDER REPORT", "label": "Provider Report", "page": "pages/21_Report_Inbox.py", "category": "research", "pattern": "phrase"},
    {"code": "DATA QUALITY REPORT", "label": "Data Quality Report", "page": "pages/21_Report_Inbox.py", "category": "research", "pattern": "phrase"},
    {"code": "KOREA MACRO", "label": "Korea Market Desk", "page": "pages/4_Macro.py", "category": "macro", "pattern": "phrase"},
    {"code": "TOOL CENTER", "label": "Research Tool Center", "page": "pages/23_Research_Tool_Center.py", "category": "research", "pattern": "phrase"},

    {"code": "OPTIONS LAB", "label": "Options Pricing & Quant Model Lab", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "PRICE OPTION", "label": "Price Option", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "SOLVE IV", "label": "Solve Implied Volatility", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "PAYOFF SCENARIO", "label": "Build Payoff Scenario", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "OPTIONS REPORT", "label": "Generate Options Report", "page": "pages/21_Report_Inbox.py", "category": "options", "pattern": "phrase"},
    {"code": "MODEL SNAPSHOT", "label": "Create Quant Model Snapshot", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "quant_model", "pattern": "phrase"},
    {"code": "OPTION CHAIN", "label": "Import Option Chain CSV", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "VOL SURFACE", "label": "Build Vol Surface Snapshot", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "OPTION BOOK", "label": "Build Option Book Risk Snapshot", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "OPTIONS CHAIN REPORT", "label": "Generate Options Chain Report", "page": "pages/21_Report_Inbox.py", "category": "options", "pattern": "phrase"},
    {"code": "SURFACE REPORT", "label": "Generate Vol Surface Report", "page": "pages/21_Report_Inbox.py", "category": "options", "pattern": "phrase"},
    {"code": "OPTION BOOK REPORT", "label": "Generate Option Book Risk Report", "page": "pages/21_Report_Inbox.py", "category": "options", "pattern": "phrase"},
    {"code": "QUANT DIAGNOSTICS", "label": "Run Local Quant Diagnostics", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "quant_model", "pattern": "phrase"},

    {"code": "SURFACE QA", "label": "Build Surface QA", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "SURFACE DIFF", "label": "Build Surface Diff", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "OPTION BOOK STRESS", "label": "Build Option Book Stress", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "HRP RMT", "label": "Run HRP RMT Diagnostic", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "quant_model", "pattern": "phrase"},
    {"code": "STATE DIAGNOSTICS", "label": "Run Kalman GARCH Diagnostic", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "quant_model", "pattern": "phrase"},
    {"code": "ATTACH MODEL RESULT", "label": "Attach Model Snapshot to Report", "page": "pages/21_Report_Inbox.py", "category": "quant_model", "pattern": "phrase"},
    {"code": "OPTIONS CASE", "label": "Create Options Research Case", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "SURFACE REVIEW", "label": "Create Surface QA Review Item", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
    {"code": "SAVE OPTION CASE", "label": "Save Options Case Artifact", "page": "pages/24_Options_Quant_Model_Lab.py", "category": "options", "pattern": "phrase"},
]

FUNCTION_ALIASES = {"FA", "KEY", "FIL", "OMON", "PORT", "CRYPTO", "ENERGY", "WATCH"}


def build_terminal_function_registry() -> list[dict[str, Any]]:
    return [dict(item) for item in FUNCTIONS]


def get_function_definition(code: str) -> dict[str, Any] | None:
    normalized = " ".join(str(code or "").upper().split())
    return next((item for item in build_terminal_function_registry() if item["code"] == normalized), None)


def search_functions(query: str) -> list[dict[str, Any]]:
    needle = str(query or "").upper().strip()
    if not needle:
        return build_terminal_function_registry()
    return [
        item
        for item in build_terminal_function_registry()
        if needle in item["code"] or needle in item["label"].upper() or needle in item["category"].upper()
    ]


def validate_command_code(code: str) -> bool:
    normalized = " ".join(str(code or "").upper().split())
    if get_function_definition(normalized):
        return True
    parts = normalized.split()
    return len(parts) == 2 and parts[1] in FUNCTION_ALIASES and parts[0].replace(".", "").replace("-", "").isalnum()


def build_function_directory_table():
    rows = build_terminal_function_registry()
    return pd.DataFrame(rows) if pd is not None else rows
