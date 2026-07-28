from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


PRODUCT_PARITY_INVENTORY_VERSION = "product_parity_inventory.v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _page(
    page: str,
    label: str,
    surface: str,
    engines: list[str],
    web_status: str,
    priority: str,
    gap: str,
) -> dict[str, Any]:
    return {
        "page": page,
        "label": label,
        "product_surface": surface,
        "primary_lib_engines": engines,
        "web_status": web_status,
        "priority": priority,
        "provider": "first-party Streamlit source",
        "source_status": "local/source-backed",
        "freshness": "repo-static",
        "caveat": "Inventory row is based on repository source, not runtime provider success.",
        "data_gap": gap,
    }


def _engine(name: str, capability: str, readiness: str, source_status: str = "local/source-backed") -> dict[str, Any]:
    return {
        "engine": name,
        "capability": capability,
        "api_readiness": readiness,
        "provider": "first-party lib",
        "source_status": source_status,
        "freshness": "repo-static",
        "caveat": "Reusable engine still requires JSON-safe boundary checks before web exposure.",
        "data_gap": "Provider runtime may still be unavailable, stale, cached, fixture, or proxy depending on source evidence.",
    }


def build_product_parity_inventory() -> dict[str, Any]:
    """Compare Streamlit product surfaces with current Phase 5A web workspaces."""
    streamlit_pages = [
        _page("pages/1_Market_Pulse.py", "Market Pulse", "Market Intelligence", ["lib/market_data.py", "lib/ai_analysis.py"], "phase5a-added", "P0", "Needs richer live/cached provider tape beyond fixture mode."),
        _page("pages/2_Stock_Analyzer.py", "Stock Analyzer", "Equity Intelligence", ["lib/equity_scenarios.py", "lib/fundamentals.py", "lib/options_flow.py"], "phase5a-added", "P0", "Live yfinance/options availability depends on provider runtime."),
        _page("pages/8_Crypto_Intelligence.py", "Crypto Intelligence", "Crypto Intelligence", ["lib/crypto_derivatives.py", "lib/crypto_prices.py", "lib/crypto_scenarios.py", "lib/crypto_onchain.py"], "phase5a-added", "P0", "Fixture mode does not claim live Binance/CoinGecko rows."),
        _page("pages/15_Financial_Terminal.py", "Financial Terminal", "Financial / Fundamentals", ["lib/financial_terminal.py", "lib/financial_charts.py"], "phase5a-partial", "P0", "Financial panels are exposed through equity-intelligence; full statement drilldowns remain partial."),
        _page("pages/24_Options_Quant_Model_Lab.py", "Options Quant Model Lab", "Options / Quant", ["lib/options_lab_page_layout.py", "lib/options_chain_iv.py", "lib/options_vol_surface.py"], "phase5a-partial", "P1", "Options/quant readiness is visible; full option book workflows remain Streamlit-only."),
        _page("pages/13_Screener.py", "Screener", "Screeners", ["lib/screeners.py", "lib/openbb_screener_backend.py"], "missing", "P1", "Dedicated web screener tables and filters are not yet migrated."),
        _page("pages/16_Portfolio_Quant_Lab.py", "Portfolio Quant Lab", "Portfolio Quant", ["lib/portfolio_quant_lab.py", "lib/portfolio_backtester.py", "lib/performance_attribution.py"], "missing", "P1", "Portfolio diagnostics remain Streamlit-only."),
        _page("pages/6_News.py", "News", "News Intelligence", ["lib/news_intelligence.py", "lib/market_impact_engine.py", "lib/catalyst_graph.py"], "covered/partial", "P1", "News fixture exists; richer impact visuals remain partial."),
        _page("pages/14_War_Room.py", "War Room", "Map-First War Room", ["lib/war_room.py", "lib/war_room_map.py", "lib/layer_registry.py"], "covered/phase5a-upgraded", "P0", "Production map renderer, live AIS, live flight, and sanctions markers remain unavailable."),
    ]
    lib_engines = [
        _engine("lib/market_data.py", "yfinance-backed market history and latest-price snapshots", "phase5a-used-live-optional"),
        _engine("lib/global_markets.py", "global proxy taxonomy for overview panels", "phase5a-used"),
        _engine("lib/equity_scenarios.py", "technical diagnostics, flow proxy, equity scenario matrix", "phase5a-used-live-optional"),
        _engine("lib/financial_terminal.py", "company header, financial overview, valuation, availability matrix", "phase5a-used-live-optional"),
        _engine("lib/financial_charts.py", "financial chart intent source", "referenced-shape-only"),
        _engine("lib/options_flow.py", "options dashboard and gamma proxy", "phase5a-readiness-only"),
        _engine("lib/crypto_derivatives.py", "Binance public derivatives snapshot and time series", "phase5a-used-live-optional"),
        _engine("lib/crypto_prices.py", "CoinGecko and Binance public price overview", "phase5a-used-live-optional"),
        _engine("lib/crypto_scenarios.py", "crypto regime and scenario matrix", "phase5a-used-live-optional"),
        _engine("lib/market_radar.py", "cross-asset and crypto radar cards", "phase5a-used-live-optional"),
        _engine("lib/war_room_map.py", "source-aware markers, layers, timeline, compare readiness", "phase5a-upgraded"),
        _engine("lib/command_workspace.py", "provider-gated terminal command routing", "phase5a-upgraded"),
    ]
    web_workspaces = [
        {"key": "market-intelligence", "route": "/api/market-intelligence", "status": "phase5a-added", "source_status": "fixture/live-optional"},
        {"key": "war-room-map", "route": "/api/war-room-map", "status": "phase5a-upgraded", "source_status": "fixture/proxy/static"},
        {"key": "equity-intelligence", "route": "/api/equity-intelligence", "status": "phase5a-added", "source_status": "fixture/live-optional"},
        {"key": "crypto-intelligence", "route": "/api/crypto-intelligence", "status": "phase5a-added", "source_status": "fixture/live-optional"},
        {"key": "event-graph", "route": "/api/event-asset-graph", "status": "covered", "source_status": "fixture/inferred/proxy"},
        {"key": "command-workspace", "route": "/api/command-workspace", "status": "phase5a-rerouted", "source_status": "provider-gated"},
        {"key": "provider-health", "route": "/api/provider-health", "status": "covered", "source_status": "fixture/missing-key"},
        {"key": "news", "route": "/api/news", "status": "covered/partial", "source_status": "fixture/live-optional"},
    ]
    missing_web_surfaces = [
        {"surface": "Dedicated screener workspace", "priority": "P1", "source_status": "missing", "data_gap": "Streamlit screener filters and heatmaps are not migrated."},
        {"surface": "Portfolio quant workspace", "priority": "P1", "source_status": "missing", "data_gap": "Portfolio backtest, attribution, and factor labs remain Streamlit-only."},
        {"surface": "Full financial statement drilldowns", "priority": "P1", "source_status": "partial", "data_gap": "Phase 5A shows overview and readiness; complete statement tables remain partial."},
        {"surface": "Full options book and volatility surface workflow", "priority": "P2", "source_status": "partial", "data_gap": "Phase 5A exposes readiness/proxy only; full option-book UX stays deferred."},
        {"surface": "Production-grade map renderer", "priority": "P2", "source_status": "partial", "data_gap": "Native map-like SVG is interactive enough for this slice; MapLibre/deck.gl remains future review."},
    ]
    priority_migration_queue = [
        {"rank": 1, "surface": "Equity Intelligence", "status": "phase5a-added", "next_step": "Wire optional runtime mode and deeper financial statements."},
        {"rank": 2, "surface": "Crypto Intelligence", "status": "phase5a-added", "next_step": "Expand live CoinGecko/Binance coverage with cache-status controls."},
        {"rank": 3, "surface": "Market Intelligence", "status": "phase5a-added", "next_step": "Add cross-asset screener and macro regime panels."},
        {"rank": 4, "surface": "War Map", "status": "phase5a-upgraded", "next_step": "Evaluate licensed map dependency or first-party map projection data."},
        {"rank": 5, "surface": "Portfolio Quant", "status": "missing", "next_step": "Move portfolio diagnostics behind JSON-safe contracts."},
    ]
    external_reference_map = [
        {"external_project": "WorldMonitor", "license_stance": "behavior-only/agpl-boundary", "adopted_behavior": "source/caveat/layer status discipline", "copied_source": False},
        {"external_project": "worldview", "license_stance": "behavior-only/nasa-license-caution", "adopted_behavior": "timeline and compare-window interaction model", "copied_source": False},
        {"external_project": "osiris", "license_stance": "mit-behavior-reference", "adopted_behavior": "OSINT layer/provider gating patterns", "copied_source": False},
        {"external_project": "OpenBB", "license_stance": "behavior-only/agpl-boundary", "adopted_behavior": "provider contract hierarchy and optional backend stance", "copied_source": False},
        {"external_project": "BB-Terminal", "license_stance": "blocked/direct-copy-not-used", "adopted_behavior": "command grammar and workstation routing behavior", "copied_source": False},
        {"external_project": "TradingView/Koyfin/Bloomberg/Refinitiv", "license_stance": "product-behavior-reference-only", "adopted_behavior": "dense chart/workstation ergonomics only", "copied_source": False},
    ]
    return {
        "product_parity_inventory_version": PRODUCT_PARITY_INVENTORY_VERSION,
        "generated_at": _now_iso(),
        "streamlit_pages": streamlit_pages,
        "lib_engines": lib_engines,
        "web_workspaces": web_workspaces,
        "missing_web_surfaces": missing_web_surfaces,
        "priority_migration_queue": priority_migration_queue,
        "external_reference_map": external_reference_map,
        "summary": {
            "streamlit_page_count": len(streamlit_pages),
            "lib_engine_count": len(lib_engines),
            "web_workspace_count": len(web_workspaces),
            "phase5a_added_workspace_count": 3,
            "missing_or_partial_surface_count": len(missing_web_surfaces),
            "external_source_copied": False,
            "broker_execution_added": False,
            "auth_billing_persistence_added": False,
            "non_advisory": True,
        },
        "caveat": "Inventory is source-backed from repository files; runtime provider availability is reported by each workspace payload.",
    }
