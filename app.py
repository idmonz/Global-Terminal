from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from lib.ai_analysis import analyze_overview_neutral
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
from lib.config import missing_optional_keys
from lib.command_history import add_command_history
from lib.env_loader import load_project_env
from lib.executive_summary_engine import build_global_executive_summary
from lib.intelligence_cards import (
    build_ai_brief_card,
    build_data_gap_cards,
    build_energy_intelligence_cards,
    build_market_intelligence_cards,
    build_news_intelligence_cards,
    build_risk_intelligence_cards,
)
import lib.map_viz as map_viz
from lib.live_feeds import fetch_live_news_feed
from lib.news_intelligence import build_worldmonitor_style_news_dashboard
from lib.overview import OVERVIEW_ASSETS, build_overview_terminal_data
from lib.executive_terminal import build_executive_terminal_brief
from lib.global_volatility_monitor import build_global_volatility_monitor
from lib.market_overview_layout import build_market_overview_payload
from lib.modern_visual_system import build_visual_system_payload
from lib.relative_market_intelligence import build_relative_market_intelligence
from lib.research_os_navigation import build_research_os_status_card
from lib.source_freshness_indicator import build_source_freshness_indicator
from lib.top_command_bar import build_top_command_bar_state
from lib.terminal_command_router import route_terminal_command
from lib.terminal_function_registry import build_function_directory_table
from lib.terminal_workspace_router import build_workspace_registry, build_workspace_status_strip
from lib.terminal_ui import (
    compact_event_card,
    freshness_badge,
    intelligence_card,
    metric_strip,
    mini_bar,
    mini_sparkline,
    modern_summary_band,
    provider_health_strip,
    severity_badge,
    source_freshness_dot,
    status_badge,
    terminal_status_console,
    terminal_ticker_tape,
    terminal_page_header,
    terminal_section_header,
    workspace_presets,
)
from lib.ui import page_footer, render_status, render_status_table, render_table

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    px = None
    go = None


st.set_page_config(page_title="Global Market Analyst Terminal", layout="wide")
load_project_env()


def _fmt(value, digits: int = 2, suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except Exception:
        return str(value)


def _empty_radar_frame(component: str = "data gap") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "component": component,
                "category": "data_gap",
                "score": 0.0,
                "label": "Data gap",
                "method": "overview payload fallback",
                "source_status": "missing",
            }
        ]
    )


def _ensure_overview_payload(payload: dict) -> dict:
    payload = payload or {}
    radar = payload.get("market_radar")
    if not isinstance(radar, dict):
        radar = {}
    radar.setdefault("cross_asset", _empty_radar_frame("cross asset"))
    radar.setdefault("equity", _empty_radar_frame("equity breadth"))
    radar.setdefault("crypto", _empty_radar_frame("crypto derivatives"))
    radar.setdefault("energy", _empty_radar_frame("energy/geopolitical"))
    radar.setdefault("volatility", _empty_radar_frame("volatility"))
    radar.setdefault(
        "composite",
        {
            "score": 0.0,
            "label": "Data gap",
            "components": 0,
            "method": "overview payload fallback",
            "is_estimated": True,
        },
    )
    payload["market_radar"] = radar
    payload.setdefault("cards", pd.DataFrame())
    payload.setdefault("chart", pd.DataFrame())
    payload.setdefault("heatmaps", {})
    payload.setdefault("crypto", {})
    payload.setdefault("equity", {})
    payload.setdefault("energy", {})
    payload.setdefault("risk", {})
    payload.setdefault("event_map", {})
    payload.setdefault("signal_convergence", pd.DataFrame())
    payload.setdefault("source_statuses", [])
    payload.setdefault("source_freshness", pd.DataFrame())
    payload.setdefault("data_gaps", ["Overview payload missing one or more expected panels."])
    return payload


def _chart(frame, view: str, ticker: str):
    if frame is None or getattr(frame, "empty", True) or px is None:
        render_table(st, frame)
        return
    data = frame.reset_index()
    x_col = data.columns[0]
    close_col = "Adj Close" if "Adj Close" in data.columns else "Close" if "Close" in data.columns else None
    if close_col is None:
        render_table(st, data)
        return
    if view == "Candlestick" and go is not None and {"Open", "High", "Low", "Close"}.issubset(data.columns):
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=data[x_col],
                    open=data["Open"],
                    high=data["High"],
                    low=data["Low"],
                    close=data["Close"],
                    name=ticker,
                )
            ]
        )
    elif view == "Performance" and "performance_pct" in data.columns:
        fig = px.line(data, x=x_col, y="performance_pct", title=f"{ticker} performance")
    elif view == "Drawdown" and "drawdown_pct" in data.columns:
        fig = px.area(data, x=x_col, y="drawdown_pct", title=f"{ticker} drawdown")
    elif view == "Realized Volatility" and "realized_volatility_pct" in data.columns:
        fig = px.line(data, x=x_col, y="realized_volatility_pct", title=f"{ticker} realized volatility")
    elif view == "Volume" and "Volume" in data.columns:
        fig = px.bar(data, x=x_col, y="Volume", title=f"{ticker} volume")
    elif view == "Relative Strength" and "performance_pct" in data.columns:
        fig = px.line(data, x=x_col, y="performance_pct", title=f"{ticker} relative performance proxy")
    else:
        fig = px.line(data, x=x_col, y=close_col, title=f"{ticker} price")
    fig.update_layout(template="plotly_dark", margin=dict(l=12, r=12, t=44, b=28))
    st.plotly_chart(fig, use_container_width=True, key=f"overview_main_chart_{ticker}_{view}")


def _radar_chart(frame, title: str):
    if px is None or frame is None or getattr(frame, "empty", True):
        render_table(st, frame)
        return
    fig = px.bar(
        frame.sort_values("score"),
        x="score",
        y="component",
        orientation="h",
        color="label",
        hover_data=["method", "source_status"] if {"method", "source_status"}.issubset(frame.columns) else None,
        title=title,
        template="plotly_dark",
    )
    fig.update_layout(margin=dict(l=8, r=8, t=42, b=24), xaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True, key=f"overview_radar_{title.lower().replace(' ', '_')}")


def _render_asset_deck(cards):
    records = cards.to_dict(orient="records") if hasattr(cards, "to_dict") else []
    cols = st.columns(6)
    for idx, row in enumerate(records):
        daily = _fmt(row.get("change_pct"), suffix="%")
        one_month = _fmt(row.get("return_1m_pct"), suffix="%")
        vol = row.get("volatility_regime") or "Data gap"
        spark = mini_sparkline(row.get("sparkline"))
        source = freshness_badge("fresh" if row.get("data_status") != "data gap" else "missing")
        html = f"""
<div class="terminal-metric">
  <div class="terminal-metric-label">{row.get("label", row.get("ticker", ""))}</div>
  <div class="terminal-metric-value">{_fmt(row.get("price"))}</div>
  <div class="terminal-metric-delta">1D {daily} | 1M {one_month}</div>
  <div class="terminal-metric-delta">{vol}</div>
  {spark}
  <div class="terminal-card-meta">{source}</div>
</div>
"""
        with cols[idx % 6]:
            st.markdown(html, unsafe_allow_html=True)


def _render_cards(cards: list[dict], columns: int = 3):
    if not cards:
        st.info("No cards available for this panel.")
        return
    cols = st.columns(max(1, min(columns, len(cards))))
    for idx, card in enumerate(cards):
        with cols[idx % len(cols)]:
            intelligence_card(
                st,
                title=card.get("title", "Card"),
                summary=card.get("summary", ""),
                severity=card.get("severity", "watch"),
                tags=card.get("tags", []),
                source=card.get("source"),
                freshness=card.get("freshness"),
            )


header_slot = st.empty()

with st.sidebar:
    st.caption("Command Router")
    workspace_registry = build_workspace_registry()
    preset = st.selectbox("Workspace preset", [item["label"] for item in workspace_registry], index=0)
    terminal_command = st.text_input("Terminal command", value="", placeholder="CC, HELP, AAPL FA, BTC CRYPTO, DATA PROBE")
    command_result = route_terminal_command(terminal_command) if terminal_command else None
    if command_result:
        add_command_history(terminal_command, command_result)
        if command_result["ok"]:
            st.success(f"{command_result['label']} -> {command_result['page']}")
        else:
            st.warning(command_result["error"])
        with st.expander("Function directory", expanded=command_result.get("command") == "HELP"):
            st.dataframe(build_function_directory_table(), use_container_width=True, hide_index=True)
    route = st.selectbox(
        "Quick select",
        ["Overview Terminal", "Research Workspace", "Watchlist & Alerts", "Report Inbox", "Strategy Decision Log", "Stock Analyzer", "Crypto Intelligence", "Global Heatmaps", "News Intelligence", "Scenario Lab", "Risk Lab", "Screener", "Portfolio Quant Lab", "Data Provider Center", "Financial Terminal", "War Room"],
        index=0,
    )
    region_focus = st.selectbox("Region focus", ["Global", "Americas", "Europe", "Middle East", "Red Sea", "Asia"], index=0)
    watchlist_focus = st.selectbox("Watchlist", ["Cross-asset core", "Equity risk", "Crypto derivatives", "Energy chokepoints"], index=0)
    show_prompt_context = st.checkbox("Show prompt context", value=False)

labels = [item["label"] for item in OVERVIEW_ASSETS]
control_cols = st.columns([1.3, 0.9, 1.25, 0.95, 1.15, 0.95, 0.95])
with control_cols[0]:
    selected_label = st.selectbox("Asset", labels, index=0)
with control_cols[1]:
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)
with control_cols[2]:
    view_options = ["Price", "Performance", "Candlestick", "Drawdown", "Realized Volatility", "Volume", "Relative Strength"]
    view = st.selectbox("Chart mode", view_options, index=0)
with control_cols[3]:
    refresh = st.button("Refresh", use_container_width=True)
with control_cols[4]:
    provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
    preferred_provider = st.selectbox("AI provider", provider_names, index=0)
with control_cols[5]:
    use_local = st.toggle("Local Ollama", value=False)
with control_cols[6]:
    show_source_status = st.toggle("Source status", value=False)

selected_ticker = next(item["ticker"] for item in OVERVIEW_ASSETS if item["label"] == selected_label)
custom_ticker = st.text_input("Custom ticker override", value="", placeholder="AAPL, SPY, BTC-USD")
ticker = (custom_ticker or selected_ticker).upper()
selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider
ai_config = select_ai_provider(selected_ai)

if refresh:
    st.cache_data.clear()

payload, overview_status = build_overview_terminal_data(ticker, period=period)
payload = _ensure_overview_payload(payload)
cards = payload["cards"]
overview_rows = cards.head(18).to_dict(orient="records") if hasattr(cards, "head") else []
rmi_payload = build_relative_market_intelligence(overview_rows)
volatility_payload = build_global_volatility_monitor(overview_rows)
wm_status = (payload.get("energy") or {}).get("worldmonitor_adapter_status", {})
mode = "local AI" if ai_config.is_local else "free" if ai_config.is_free_mode else "optional-key"
freshness_summary = overview_status.refreshed_status() if overview_status is not None else "unknown"
modern_payload = build_visual_system_payload(
    "Overview",
    "Summary-first cross-asset launchpad with heatmaps, RMI, volatility, events, and provider confidence.",
    context={
        "freshness": freshness_summary,
        "confidence": (payload.get("market_radar") or {}).get("composite", {}).get("score", 50),
        "provider_gaps": payload.get("data_gaps", []),
        "risk_state": (payload.get("market_radar") or {}).get("composite", {}).get("label", "watch"),
    },
)
command_bar_state = build_top_command_bar_state(
    terminal_command,
    route_result=command_result,
    freshness=build_source_freshness_indicator("overview", status=freshness_summary, confidence=modern_payload["header"]["confidence"]["value"]),
)
market_overview_payload = build_market_overview_payload(
    context={
        "risk_state": (payload.get("market_radar") or {}).get("composite", {}).get("label", "watch"),
        "data_confidence": modern_payload["header"]["confidence"]["value"],
        "source_freshness": freshness_summary,
        "provider_gaps": payload.get("data_gaps", []),
    },
    cross_asset_rows=overview_rows,
    equity_rows=overview_rows,
    crypto_rows=overview_rows,
    provider_rows=[{"provider_id": "overview", "domain": "terminal", "score": modern_payload["header"]["confidence"]["value"], "status": freshness_summary}],
    rmi=rmi_payload,
    volatility=volatility_payload,
)

with header_slot.container():
    terminal_page_header(
        st,
        "Global Market Analyst Terminal",
        "Cross-asset command center for market structure, source status, news risk, and neutral AI context.",
        meta=[
            {"label": "Timestamp", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"label": "Freshness", "value": freshness_summary, "tone": freshness_summary},
            {"label": "AI", "value": f"{ai_config.provider} / {ai_config.model}", "tone": "fresh" if ai_config.available else "estimated"},
            {"label": "WorldMonitor", "value": wm_status.get("status", "not configured"), "tone": wm_status.get("status", "missing")},
            {"label": "Mode", "value": mode, "tone": "info"},
        ],
    )
    provider_health_strip(st)
    st.markdown(source_freshness_dot(command_bar_state["freshness"]), unsafe_allow_html=True)
    modern_summary_band(
        st,
        title="Modern Intelligence Launchpad",
        bullets=[
            "Start with the executive summary, then inspect heatmaps, RMI, volatility, events, and provider gaps.",
            f"Command help is available with {command_bar_state['help']['count']} research shortcuts; commands never execute trades.",
            f"Current source state: {freshness_summary}.",
            f"Personal Research OS status: {build_research_os_status_card()['summary']}.",
        ],
        keywords=modern_payload["summary"]["keywords"],
        actions=market_overview_payload["click_next"][:6],
    )
    st.caption("Workspace status: " + " | ".join(f"{item['label']}={item['value']}" for item in build_workspace_status_strip(preset)))

missing = [key for key, is_missing in missing_optional_keys().items() if is_missing]
if missing:
    st.caption("Optional keys missing: " + ", ".join(missing))
render_status(st, overview_status)

executive = build_executive_terminal_brief(
    payload,
    overview_status,
    route=route,
    region_focus=region_focus,
    watchlist_focus=watchlist_focus,
)
goal10_executive = build_global_executive_summary(
    {
        "risk_score": (payload.get("market_radar") or {}).get("composite", {}).get("score"),
        "data_gaps": payload.get("data_gaps", []),
        "affected_assets": [ticker],
        "provider_health": {"available": 1, "optional_missing": len(missing)},
        "source_confidence": (payload.get("market_radar") or {}).get("composite", {}).get("score", 50),
        "proxy_outputs": ["energy risk proxy", "options gamma proxy", "scenario estimates"],
        "official_outputs": ["static index constituents"],
    }
)
terminal_section_header(st, "Executive Brief", "Condensed operator read across market tape, data quality, and terminal routing.")
metric_strip(st, executive["metrics"], columns=5)
metric_strip(
    st,
    [
        {"label": "Goal 10 Risk State", "value": goal10_executive["global_risk_state"], "delta": "summary", "freshness": "estimated"},
        {"label": "Data Confidence", "value": goal10_executive["data_confidence"]["score"], "delta": "source score", "freshness": "estimated"},
        {"label": "Provider Gaps", "value": goal10_executive["provider_health"]["gap_count"], "delta": "nonfatal", "freshness": "missing" if goal10_executive["provider_health"]["gap_count"] else "fresh"},
    ],
    columns=3,
)
brief_cols = st.columns([1.2, 1.2, 1])
with brief_cols[0]:
    _render_cards(executive["cards"][:2], columns=1)
with brief_cols[1]:
    _render_cards(executive["cards"][2:], columns=1)
with brief_cols[2]:
    render_table(st, executive["movers"])
    with st.expander("Connected Workflows", expanded=False):
        render_table(st, executive["route_map"])
        for note in executive["operator_notes"]:
            st.caption(note)

terminal_section_header(st, "Cross-Asset Metric Deck", "Daily tape, 1M trend, realized volatility regime, and source state.")
_render_asset_deck(cards)
tape = terminal_ticker_tape(cards.head(12).rename(columns={"price": "value", "change_pct": "delta"}).to_dict(orient="records") if hasattr(cards, "head") else [])
st.markdown(tape["html"], unsafe_allow_html=True)

main_left, main_right = st.columns([2.2, 1])
with main_left:
    terminal_section_header(st, "Market Tape", f"Selected asset: {ticker}")
    _chart(payload["chart"], view, ticker)
with main_right:
    terminal_section_header(st, "AI And Watch-Points", "Button-triggered neutral brief with explicit data gaps.")
    _render_cards([build_ai_brief_card(context={"provider": ai_config.provider, "model": ai_config.model})], columns=1)
    for point in [
        f"Route: {route}",
        f"Region focus: {region_focus}",
        f"Watchlist: {watchlist_focus}",
        "AIS and dealer-confirmed gamma require real providers.",
    ]:
        st.markdown(mini_bar(45, label=point, color="#38bdf8"), unsafe_allow_html=True)
    context = {
        "cards": cards.head(12).to_dict(orient="records") if hasattr(cards, "head") else cards,
        "risk": payload["risk"],
        "crypto": payload["crypto"],
        "equity": payload["equity"],
        "energy": "energy panel available; detailed frame omitted from prompt",
        "data_gaps": payload["data_gaps"],
        "source_freshness": payload.get("source_freshness").to_dict(orient="records") if hasattr(payload.get("source_freshness"), "to_dict") else [],
    }
    if show_prompt_context:
        with st.expander("Prompt context", expanded=False):
            st.json(redact_secrets(str(context)))
    if st.button("Generate neutral AI summary", key="overview_ai"):
        response = analyze_overview_neutral(context, preferred=selected_ai)
        st.markdown(response.text)
        st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")

terminal_section_header(st, "Market Radar", "Normalized heuristic radar components. Scores are not predictions.")
radar_cols = st.columns([1.2, 1.2, 1])
with radar_cols[0]:
    combined_radar = pd.concat(
        [
            payload["market_radar"]["equity"],
            payload["market_radar"]["crypto"],
            payload["market_radar"]["energy"],
            payload["market_radar"]["volatility"],
        ],
        ignore_index=True,
    )
    _radar_chart(combined_radar, "Risk And Breadth Radar")
with radar_cols[1]:
    _radar_chart(payload["market_radar"]["cross_asset"].head(12), "Cross-Asset Move Radar")
with radar_cols[2]:
    composite = payload["market_radar"]["composite"]
    intelligence_card(
        st,
        title="Cross-Asset Composite",
        summary=f"{composite['label']} from {composite['components']} components.",
        severity="medium" if composite["score"] >= 60 else "watch",
        tags=["heuristic", "composite"],
        source="market_radar",
        freshness="estimated",
    )
    st.markdown(mini_bar(composite["score"], label="Composite score", color="#f59e0b"), unsafe_allow_html=True)
    render_table(st, payload["signal_convergence"])

terminal_section_header(st, "Relative Market Intelligence And Volatility", "Leader/laggard context and volatility risk state. Research-only rankings.")
rmi_cols = st.columns([1.1, 1.1, 0.8])
with rmi_cols[0]:
    st.markdown("#### RMI Table")
    render_table(st, pd.DataFrame(rmi_payload["table"])[["symbol", "relative_strength_score", "relative_state", "benchmark", "freshness"]] if rmi_payload["table"] else pd.DataFrame())
with rmi_cols[1]:
    st.markdown("#### Volatility Ranking")
    render_table(st, pd.DataFrame(volatility_payload["ranking"])[["symbol", "volatility_zscore", "drawdown_state", "volatility_state", "risk_score"]] if volatility_payload["ranking"] else pd.DataFrame())
with rmi_cols[2]:
    for card in rmi_payload["cards"][:2] + volatility_payload["cards"][:1]:
        intelligence_card(st, title=card["title"], summary=card["summary"], severity=card["severity"], tags=card["tags"], freshness=card["freshness"])

terminal_section_header(st, "Heatmap Strip", "Compact cross-section views; full detail remains on Global Heatmaps.")
heatmap_tabs = st.tabs(["US sectors", "Crypto", "Cross-asset"])
for tab, key in zip(heatmap_tabs, ["sectors", "crypto", "cross_asset"]):
    with tab:
        render_table(st, payload["heatmaps"].get(key))
with st.expander("Goal 10B Heatmap Payloads", expanded=False):
    render_table(st, market_overview_payload["market_board"]["cross_asset_heatmap"]["table"])
    render_table(st, market_overview_payload["market_board"]["provider_health_heatmap"]["table"])

terminal_section_header(st, "WorldMonitor-Style Intelligence", "Source-backed public feed rows or explicit unavailable states; no external WorldMonitor code is imported.")
overview_news, overview_news_status = fetch_live_news_feed(query="geopolitical risk OR oil OR macro OR crypto")
news_dashboard = build_worldmonitor_style_news_dashboard(overview_news, [overview_news_status])
render_status(st, overview_news_status)
map_left, map_mid, map_right = st.columns([1.25, 1.25, 1])
with map_left:
    build_chokepoint_risk_map = getattr(map_viz, "build_chokepoint_risk_map", map_viz.build_chokepoint_map)
    chokepoint_fig, chokepoint_frame, chokepoint_status = build_chokepoint_risk_map()
    if chokepoint_fig is not None:
        st.plotly_chart(chokepoint_fig, use_container_width=True, key="overview_chokepoint_risk_map")
    else:
        render_table(st, chokepoint_frame)
    render_status(st, chokepoint_status)
with map_mid:
    build_market_region_risk_map = getattr(map_viz, "build_market_region_risk_map", map_viz.build_market_region_map)
    region_fig, region_frame, region_status = build_market_region_risk_map()
    if region_fig is not None:
        st.plotly_chart(region_fig, use_container_width=True, key="overview_market_region_risk_map")
    else:
        render_table(st, region_frame)
    render_status(st, region_status)
with map_right:
    _render_cards(build_energy_intelligence_cards(payload.get("energy")), columns=1)
    _render_cards(build_news_intelligence_cards(news_dashboard), columns=1)

terminal_section_header(st, "Terminal Intelligence Cards", "Market, risk, data gaps, and source freshness in compact form.")
card_tabs = st.tabs(["Market", "Risk", "Data Gaps", "Source Freshness"])
with card_tabs[0]:
    _render_cards(build_market_intelligence_cards(payload), columns=3)
with card_tabs[1]:
    _render_cards(build_risk_intelligence_cards(payload.get("risk")), columns=3)
with card_tabs[2]:
    _render_cards(build_data_gap_cards(payload.get("data_gaps"), payload.get("source_statuses")), columns=3)
with card_tabs[3]:
    render_table(st, payload.get("source_freshness"))

terminal_section_header(st, "Bottom Snapshot Row", "Screener, financial, options, and stress context remain compact on overview.")
bottom_cols = st.columns(4)
with bottom_cols[0]:
    st.markdown("#### Screener Snapshot")
    if hasattr(cards, "sort_values"):
        snapshot_cols = [col for col in ["label", "price", "return_1m_pct", "realized_volatility_pct", "volatility_regime"] if col in cards.columns]
        render_table(st, cards[snapshot_cols].sort_values("return_1m_pct", ascending=False).head(8))
with bottom_cols[1]:
    st.markdown("#### Financial Overview")
    if ticker.startswith("^") or ticker.endswith("-USD") or ticker.endswith("=F"):
        intelligence_card(st, title="Selected Asset Not A Stock", summary="Financial statements are shown on the Stock Analyzer for single-name equities.", severity="watch", tags=["data gap"], freshness="missing")
    else:
        intelligence_card(st, title=f"{ticker} Financial Snapshot", summary="Detailed revenue, margin, cash-flow, and balance panels are available in Stock Analyzer.", severity="watch", tags=["financial overview"], freshness="estimated")
with bottom_cols[2]:
    st.markdown("#### Options / Gamma Proxy")
    if ticker.startswith("^") or ticker.endswith("-USD") or ticker.endswith("=F"):
        intelligence_card(st, title="Gamma Proxy Unavailable", summary="Options chain proxy is applicable to supported tickers with yfinance option chains.", severity="watch", tags=["proxy", "data gap"], freshness="missing")
    else:
        intelligence_card(st, title=f"{ticker} Options Proxy", summary="Open-interest and gamma proxy panels are available on the Stock Analyzer. Dealer-confirmed GEX is not claimed.", severity="watch", tags=["options", "proxy"], freshness="estimated")
with bottom_cols[3]:
    st.markdown("#### Risk Stress Mini-Panel")
    for event in (payload.get("event_map") or {}).get("timeline", pd.DataFrame()).to_dict(orient="records") if hasattr((payload.get("event_map") or {}).get("timeline"), "to_dict") else []:
        compact_event_card(st, event)

if show_source_status:
    with st.expander("Full Source Status", expanded=True):
        render_status_table(st, payload["source_statuses"])

console = terminal_status_console(
    [
        {"source": "workspace", "status": "preset", "message": preset},
        {"source": "route", "status": "selected", "message": route},
        {"source": "provider", "status": freshness_summary, "message": overview_status.coverage if overview_status is not None else "No status"},
    ]
)
terminal_section_header(st, "Status Console", "Session-level command log and provider state.")
st.markdown(console["html"], unsafe_allow_html=True)

page_footer(st)
