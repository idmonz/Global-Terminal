from __future__ import annotations

import streamlit as st

from lib.ai_analysis import analyze_energy_geopolitical_neutral
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
from lib.energy_data import build_energy_fundamentals_dashboard, build_unified_energy_dashboard, get_eia_api_key_status, get_yfinance_energy_fallback
from lib.geopolitical_news import build_geopolitical_news_dashboard
from lib.map_viz import build_chokepoint_map, build_energy_route_map_proxy
from lib.oil_flows import build_chokepoint_registry, compute_chokepoint_risk_proxy, compute_oil_scenario_matrix, compute_shipping_disruption_proxy
from lib.shipping_chokepoint_engine import build_chokepoint_risk_cards
from lib.live_feeds import fetch_aisstream_optional_status
from lib.energy_geopolitics_map import build_energy_geopolitics_map_payload
from lib.heatmap_layout_engine import build_energy_risk_heatmap
from lib.terminal_ui import energy_terminal_payload, goal10_summary_strip, intelligence_card, metric_strip, modern_summary_band, provider_health_strip, terminal_page_header, terminal_section_header
from lib.ui import page_footer, render_status, render_status_table, render_table
from lib.worldmonitor_adapter import check_worldmonitor_status, get_route_intelligence, get_supply_chain_chokepoints


st.set_page_config(page_title="Energy & Geopolitics", layout="wide")
terminal_page_header(
    st,
    "Energy & Geopolitics",
    "Oil fundamentals, chokepoint risk, route proxies, EIA freshness, and War Room links.",
    meta=[
        {"label": "AIS", "value": "optional/unavailable", "tone": "estimated"},
        {"label": "EIA", "value": "optional key", "tone": "estimated"},
        {"label": "Maps", "value": "proxy-labeled", "tone": "fresh"},
    ],
)
provider_health_strip(st)
goal10_summary_strip(st, workspace="Energy / Geopolitics Desk", risk_state="watch", data_confidence="EIA/proxy labeled", provider_status="AIS optional", caveat="Oil fundamentals, chokepoints, and route maps are source-labeled; live AIS is unavailable unless configured and tested.")
energy_payload = energy_terminal_payload()
energy_map_payload = build_energy_geopolitics_map_payload()
energy_heatmap = build_energy_risk_heatmap(energy_map_payload["chokepoint_layer"])
ais_status = fetch_aisstream_optional_status()
metric_strip(
    st,
    [
        {"label": "Chokepoint Board", "value": 1, "delta": "enabled", "freshness": "estimated"},
        {"label": "Oil Risk Premium", "value": 1, "delta": "proxy", "freshness": "estimated"},
        {"label": "EIA Cards", "value": 1, "delta": "optional", "freshness": "estimated"},
        {"label": "AIS", "value": 0 if not ais_status["available"] else 1, "delta": ais_status["status"], "freshness": "missing" if not ais_status["available"] else "fresh"},
    ],
)
if ais_status["warning"]:
    st.warning(ais_status["warning"])
st.page_link("pages/14_War_Room.py", label="Open War Room", icon=":material/radar:")
modern_summary_band(
    st,
    title="Energy Map Intelligence",
    bullets=[
        "Chokepoints, shipping, weather, and news layers are source-labeled and proxy-aware.",
        "NOAA AccessAIS remains historical-only; AISStream is live only after key and successful probe.",
        "Oil/gas asset impact is research context, not direction advice.",
    ],
    keywords=[
        {"label": "chokepoints", "category": "energy/geopolitics", "importance": "high"},
        {"label": "AIS historical-only", "category": "data freshness", "importance": "high"},
        {"label": "EIA optional key", "category": "provider issue", "importance": "medium"},
    ],
    actions=[
        {"label": "Open War Room", "description": "Inspect regional event layers and source gaps.", "command": "WR", "page": "pages/14_War_Room.py"},
        {"label": "Verify energy providers", "description": "Review EIA, weather, AIS, and news probe states.", "command": "DATA PROBE energy", "page": "pages/17_Data_Provider_Center.py"},
    ],
)

oil_benchmark = st.sidebar.selectbox("Oil benchmark", ["WTI", "Brent"])
futures_ticker = st.sidebar.selectbox("Futures ticker", ["CL=F", "BZ=F"])
period = st.sidebar.selectbox("Lookback period", ["3mo", "6mo", "1y"], index=1)
enable_eia = st.sidebar.checkbox("Enable EIA data", value=True)
source_mode = st.sidebar.selectbox("Unified source mode", ["auto", "native_only", "openbb_preferred", "openbb_only"], index=0)
enable_worldmonitor = st.sidebar.checkbox("Enable WorldMonitor optional adapter", value=False)
enable_news = st.sidebar.checkbox("Enable GDELT/RSS news proxy", value=False)
chokepoint = st.sidebar.selectbox("Chokepoint", build_chokepoint_registry()["name"].tolist())
provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
preferred_provider = st.sidebar.selectbox("AI provider", provider_names, index=0)
use_local = st.sidebar.checkbox("Use local Ollama if available", value=False)
show_prompt_context = st.sidebar.checkbox("Show prompt context", value=False)
selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider

tabs = st.tabs(
    [
        "Oil Market Overview",
        "EIA Fundamentals",
        "Inventory & Storage",
        "Production / Imports / Exports",
        "Refinery & Products",
        "Shipping & Chokepoints",
        "Geopolitical Risk News",
        "Energy Scenario Monitor",
        "Map / Routes",
        "WorldMonitor Adapter",
        "AI Brief",
        "Data Status",
    ]
)

with tabs[0]:
    unified_energy = build_unified_energy_dashboard(source_mode=source_mode)
    terminal_section_header(st, "Unified Energy Backend", "Native/OpenBB-compatible routes with proxy and data-gap labels.")
    st.caption(unified_energy["caveat"])
    render_table(st, unified_energy["status_table"])
    render_table(st, unified_energy["market_impact_cards"])
    fallback, status = get_yfinance_energy_fallback(period=period)
    render_status(st, status)
    render_table(st, fallback)
with tabs[1]:
    data, status = build_energy_fundamentals_dashboard(enable_eia=enable_eia)
    render_status(st, status)
    for name, frame in data.items():
        st.subheader(name.replace("_", " ").title())
        render_table(st, frame)
with tabs[2]:
    data, status = build_energy_fundamentals_dashboard(enable_eia=enable_eia)
    render_status(st, status)
    for name in ["crude_inventories", "cushing_inventories", "spr_stocks", "gasoline_stocks", "distillate_stocks"]:
        st.subheader(name.replace("_", " ").title())
        render_table(st, data.get(name))
with tabs[3]:
    data, status = build_energy_fundamentals_dashboard(enable_eia=enable_eia)
    render_status(st, status)
    for name in ["production", "imports", "exports"]:
        st.subheader(name.title())
        render_table(st, data.get(name))
with tabs[4]:
    data, status = build_energy_fundamentals_dashboard(enable_eia=enable_eia)
    render_status(st, status)
    for name in ["refinery_utilization", "gasoline_stocks", "distillate_stocks", "product_supplied"]:
        st.subheader(name.replace("_", " ").title())
        render_table(st, data.get(name))
with tabs[5]:
    terminal_section_header(st, "Chokepoint Risk Board", "Static chokepoint registry and shipping disruption proxy; no live vessel flow is claimed.")
    render_table(st, build_chokepoint_risk_cards())
    risk_table, risk_status = compute_chokepoint_risk_proxy(selected=chokepoint)
    render_status(st, risk_status)
    render_table(st, risk_table)
    proxy, proxy_status = compute_shipping_disruption_proxy()
    render_status(st, proxy_status)
    st.json(proxy)
with tabs[6]:
    if enable_news:
        payload, status = build_geopolitical_news_dashboard()
        render_status(st, status)
        render_table(st, payload.get("news"))
        st.json(payload.get("risk", {}))
    else:
        st.info("News proxy disabled in sidebar.")
with tabs[7]:
    scenarios, status = compute_oil_scenario_matrix({"asset": futures_ticker, "horizon": "1m"})
    render_status(st, status)
    render_table(st, scenarios)
with tabs[8]:
    terminal_section_header(st, "Layered Route / Chokepoint Map", "Route arcs are exposure proxies and AIS is optional.")
    fig, chokepoints, map_status = build_chokepoint_map()
    render_status(st, map_status)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    render_table(st, chokepoints)
    route_fig, route_rows, route_status = build_energy_route_map_proxy()
    render_status(st, route_status)
    if route_fig is not None:
        st.plotly_chart(route_fig, use_container_width=True)
    terminal_section_header(st, "Goal 10B Energy Map Payload", "Chokepoint, shipping, weather, news, impact, and data-quality layers.")
    render_table(st, energy_heatmap["table"])
    render_table(st, energy_map_payload["data_quality"])
    render_table(st, energy_map_payload["asset_impact_panel"].get("cards"))
with tabs[9]:
    wm_status = check_worldmonitor_status() if enable_worldmonitor else get_eia_api_key_status()
    render_status(st, wm_status)
    if enable_worldmonitor:
        route_status = get_route_intelligence("US", "KR")
        chokepoints_status = get_supply_chain_chokepoints()
        render_status_table(st, [wm_status, route_status, chokepoints_status])
with tabs[10]:
    st.caption(f"Provider: {select_ai_provider(selected_ai).provider} | Model: {select_ai_provider(selected_ai).model}")
    context = {
        "oil_benchmark": oil_benchmark,
        "futures_ticker": futures_ticker,
        "chokepoint": chokepoint,
        "worldmonitor_enabled": enable_worldmonitor,
        "data_gaps": "EIA, WorldMonitor, AIS, and public news feeds are optional or rate-limited.",
    }
    if show_prompt_context:
        with st.expander("Prompt context", expanded=False):
            st.json(redact_secrets(str(context)))
    if st.button("Generate neutral AI summary", key="energy_ai"):
        response = analyze_energy_geopolitical_neutral(context, preferred=selected_ai)
        st.markdown(response.text)
        st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")
with tabs[11]:
    render_status_table(st, [get_eia_api_key_status()])
    intelligence_card(
        st,
        title="Energy Data Caveat",
        summary=energy_payload["caveat"],
        severity="watch",
        tags=["EIA", "AIS", "proxy"],
        source="energy terminal payload",
        freshness="estimated",
    )

page_footer(st)
