from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


WORKSPACES: list[dict[str, Any]] = [

    {"label": "Global Command Center", "purpose": "Cross-asset executive brief and provider status", "primary_pages": ["app.py", "pages/19_Research_Workspace.py", "pages/20_Watchlist_Alerts.py", "pages/21_Report_Inbox.py", "pages/22_Strategy_Decision_Log.py"], "key_widgets": ["Executive Brief", "Command Bar", "Provider Health", "Research Workspace"], "default_drilldowns": ["DATA PROBE", "GLOBAL WAR", "WORKSPACE", "WATCHLIST", "REPORTS", "STRATEGY LOG"], "required_data": ["price history"], "optional_data": ["AI provider", "OpenBB"], "data_gaps": [], "caveats": ["Summary-first view uses available public/provider data."]},
    {"label": "Equity Desk", "purpose": "Equity fundamentals, screeners, and security scorecards", "primary_pages": ["pages/13_Screener.py", "pages/15_Financial_Terminal.py"], "key_widgets": ["Screener", "Scorecard", "Financial charts"], "default_drilldowns": ["AAPL FA", "AAPL KEY"], "required_data": ["price history"], "optional_data": ["SEC_USER_AGENT", "OpenBB"], "data_gaps": ["Analyst estimates may require optional providers."], "caveats": ["Filings require user-agent setup."]},
    {"label": "Crypto Derivatives Desk", "purpose": "Funding, open interest, on-chain, and derivatives stress", "primary_pages": ["pages/8_Crypto_Intelligence.py"], "key_widgets": ["Funding", "OI", "Derivatives radar"], "default_drilldowns": ["BTC CRYPTO"], "required_data": ["public crypto prices"], "optional_data": ["COINGECKO_API_KEY"], "data_gaps": ["Liquidation heatmaps require official providers."], "caveats": ["Liquidation pressure is proxy unless labeled official."]},
    {"label": "Energy / Geopolitics Desk", "purpose": "Oil, shipping, chokepoints, and event risk", "primary_pages": ["pages/9_Energy_Geopolitics.py", "pages/14_War_Room.py"], "key_widgets": ["Chokepoint board", "Energy risk proxy"], "default_drilldowns": ["CL ENERGY", "GLOBAL WAR"], "required_data": ["public commodity data"], "optional_data": ["EIA_API_KEY", "AISSTREAM_API_KEY"], "data_gaps": ["Live AIS unavailable unless optional setup is configured and tested."], "caveats": ["Shipping status is not live unless provider probe succeeds."]},
    {"label": "Portfolio Quant Lab", "purpose": "Research portfolios, strategy candidates, and validation", "primary_pages": ["pages/16_Portfolio_Quant_Lab.py"], "key_widgets": ["Backtest", "Alpha Workbench", "Risk Budget"], "default_drilldowns": ["SPY PORT", "STRAT WORKBENCH"], "required_data": ["price history"], "optional_data": ["OpenBB factor backend"], "data_gaps": ["Factor coverage may be proxy."], "caveats": ["Backtests are research-only."]},
    {"label": "Risk Manager", "purpose": "Stress tests, scenarios, and portfolio drawdown context", "primary_pages": ["pages/11_Risk_Lab.py", "pages/10_Scenario_Lab.py"], "key_widgets": ["Stress matrix", "Scenario engine"], "default_drilldowns": ["RISK LAB"], "required_data": ["portfolio inputs"], "optional_data": ["macro providers"], "data_gaps": ["Scenario reactions are estimates."], "caveats": ["Scenario outputs are not forecasts."]},
    {"label": "Financial Terminal", "purpose": "Financial statements, ratios, filings, and charts", "primary_pages": ["pages/15_Financial_Terminal.py"], "key_widgets": ["Statements", "Ratios", "Filings"], "default_drilldowns": ["AAPL FA", "AAPL FIL"], "required_data": ["ticker"], "optional_data": ["SEC_USER_AGENT", "OpenBB"], "data_gaps": ["Some estimates require optional providers."], "caveats": ["Financial payloads may be delayed or provider-limited."]},
    {"label": "News / OSINT War Room", "purpose": "WorldMonitor-style event map and source-labeled OSINT", "primary_pages": ["pages/14_War_Room.py", "pages/6_News.py"], "key_widgets": ["Event map", "Layer registry", "Source freshness"], "default_drilldowns": ["GLOBAL WAR"], "required_data": ["public news/events"], "optional_data": ["WORLD_MONITOR_BASE_URL"], "data_gaps": ["Some layers are unavailable without provider setup."], "caveats": ["OSINT is source-labeled and may be delayed."]},
    {"label": "OpenBB / Data Provider Desk", "purpose": "Provider probes, optional OpenBB bridge, and key readiness", "primary_pages": ["pages/17_Data_Provider_Center.py", "pages/18_OpenBB_Data_Hub.py"], "key_widgets": ["Provider probes", "Env status", "OpenBB catalog"], "default_drilldowns": ["DATA PROBE", "OPENBB HUB"], "required_data": [], "optional_data": ["OpenBB", "free API keys"], "data_gaps": ["Missing keys are visible but nonfatal."], "caveats": ["User must verify licensing and data rights."]},
    {"label": "Korea Market Desk", "purpose": "Korea macro, equity watchlists, and optional official APIs", "primary_pages": ["pages/4_Macro.py", "pages/7_Global_Heatmaps.py"], "key_widgets": ["Korea watchlist", "Macro panels"], "default_drilldowns": ["KOREA MACRO"], "required_data": ["static watchlist"], "optional_data": ["BOK_ECOS_API_KEY", "OPENDART_API_KEY", "KOSIS_API_KEY", "KRX_API_KEY"], "data_gaps": ["Official Korea APIs require free keys where available."], "caveats": ["KRX/open public data terms must be verified."]},
]


def build_workspace_registry() -> list[dict[str, Any]]:
    return [dict(item) for item in WORKSPACES]


def get_workspace_definition(label: str) -> dict[str, Any] | None:
    needle = str(label or "").lower()
    return next((item for item in build_workspace_registry() if item["label"].lower() == needle), None)


def route_workspace_payload(label: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    workspace = get_workspace_definition(label) or build_workspace_registry()[0]
    gaps = list(workspace.get("data_gaps", [])) + list((context or {}).get("data_gaps", []))
    return {**workspace, "active": True, "data_gaps": gaps, "context": context or {}}


def build_workspace_nav_cards() -> list[dict[str, Any]]:
    return [
        {
            "title": item["label"],
            "summary": item["purpose"],
            "tags": item["default_drilldowns"],
            "page": item["primary_pages"][0],
            "freshness": "estimated" if item.get("optional_data") else "fresh",
        }
        for item in build_workspace_registry()
    ]


def build_workspace_status_strip(label: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = route_workspace_payload(label, context)
    return [
        {"label": "Workspace", "value": payload["label"], "freshness": "fresh"},
        {"label": "Pages", "value": len(payload["primary_pages"]), "freshness": "fresh"},
        {"label": "Optional Data", "value": len(payload["optional_data"]), "freshness": "estimated"},
        {"label": "Data Gaps", "value": len(payload["data_gaps"]), "freshness": "missing" if payload["data_gaps"] else "fresh"},
    ]


def build_workspace_default_page(label: str) -> str:
    workspace = get_workspace_definition(label) or build_workspace_registry()[0]
    return workspace["primary_pages"][0]
