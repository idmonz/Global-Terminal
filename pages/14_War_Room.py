from __future__ import annotations

import streamlit as st

from lib.api_contract_panels import contract_preview, contract_summary_rows
from lib.api_contracts import build_api_war_room_payload
from lib.ai_providers import list_available_ai_providers
from lib.data_status import get_recent_results
from lib.geopolitical_news import build_multi_source_news_feed, build_oil_news_query
from lib.terminal_ui import (
    compact_event_card,
    data_gap_badge,
    freshness_badge,
    goal10_summary_strip,
    intelligence_card,
    layer_control_payload,
    metric_strip,
    modern_summary_band,
    mini_bar,
    provider_health_strip,
    severity_badge,
    status_badge,
    terminal_page_header,
    terminal_section_header,
    war_room_right_rail_panels,
    workspace_presets,
)
from lib.ui import page_footer, render_status, render_table
from lib.war_room import build_data_gap_panel, build_war_room_state
from lib.war_room_live_data_router import build_war_room_live_payload
from lib.heatmap_layout_engine import build_war_room_region_heatmap


st.set_page_config(page_title="Global War Room", layout="wide")

available_ai = [provider for provider in list_available_ai_providers() if provider.available]
ai_status = "available" if available_ai else "not configured"

with st.sidebar:
    st.subheader("Command Router")
    preset = st.selectbox("Workspace preset", [item["name"] for item in workspace_presets()], index=7)
    mode = st.selectbox("Mode", ["Global Command Center", "Equity Desk", "Crypto Derivatives Desk", "Energy / Geopolitics Desk", "Portfolio Quant Lab", "Risk Manager", "Financial Terminal", "News / OSINT War Room"], index=7)
    query = st.text_input("News query", build_oil_news_query())
    fetch_news = st.checkbox("Fetch public news feed", value=False)
    layer_search = st.text_input("Search layers", "")
    layer_domain = st.selectbox("Layer domain", ["All", "geopolitical", "energy", "infrastructure", "natural", "market", "crypto", "osint"], index=0)
    selected_layers = st.multiselect(
        "Map layers",
        ["events", "chokepoints", "routes"],
        default=["events", "chokepoints", "routes"],
    )
    time_range = st.selectbox("Time range", ["1h", "6h", "24h", "7d", "30d", "all"], index=2)
    region_filter = st.selectbox("Region", ["All", "Global", "Americas", "Europe", "MENA", "Asia", "Korea", "Energy chokepoints", "Custom"], index=0)
    custom_context = st.text_input("Custom ticker / region", "")
    provider_health_strip(st)

news_rows = None
news_status = None
if fetch_news:
    payload, news_status = build_multi_source_news_feed(query)
    news_rows = payload.get("news")

state = build_war_room_state(news=news_rows, layers=selected_layers, statuses=get_recent_results(), include_default_runtime=True)
live_payload = build_war_room_live_payload(state["events"])
region_heatmap = build_war_room_region_heatmap(
    [
        {
            "region": cluster.get("region"),
            "event_count": cluster.get("count"),
            "risk_score": cluster.get("severity_score"),
            "source": "war_room_live_payload",
            "freshness": "estimated",
            "tile_type": "region",
        }
        for cluster in live_payload["clusters"]
    ]
)
header = state["header_metrics"]

terminal_page_header(
    st,
    "Global War Room",
    "Map-first global intelligence surface for markets, energy, crypto, geopolitics, chokepoints, and data gaps.",
    meta=[
        {"label": "UTC", "value": header["utc_timestamp"], "tone": "info"},
        {"label": "Local", "value": header["local_timestamp"], "tone": "info"},
        {"label": "Risk state", "value": header["global_risk_state"], "tone": header["global_risk_state"]},
        {"label": "AI provider", "value": ai_status, "tone": "fresh" if available_ai else "missing"},
        {"label": "WorldMonitor adapter", "value": state["worldmonitor_adapter_status"], "tone": "fresh" if state["worldmonitor_adapter_status"] == "configured" else "missing"},
        {"label": "Freshness", "value": header["data_freshness_summary"], "tone": "estimated"},
        {"label": "Mode", "value": mode, "tone": "info"},
        {"label": "Preset", "value": preset, "tone": "info"},
    ],
)
goal10_summary_strip(
    st,
    workspace="News / OSINT War Room",
    risk_state=header["global_risk_state"],
    data_confidence=header["data_freshness_summary"],
    provider_status=f"{header['available_layers']} layers available",
    caveat="Events, maps, layers, and chokepoints are source-labeled; unavailable live AIS/flight layers remain explicit data gaps.",
)

if news_status is not None:
    render_status(st, news_status)

metrics = [
    {"label": "Global Risk Score", "value": header["global_risk_score"], "delta": header["global_risk_state"], "freshness": "estimated"},
    {"label": "Available Layers", "value": header["available_layers"], "delta": f"{header['optional_layers']} optional", "freshness": "fresh"},
    {"label": "Events", "value": len(state["events"]), "delta": time_range, "freshness": "estimated"},
    {"label": "Source Gaps", "value": header["missing_or_error_sources"], "delta": "missing/error", "freshness": "missing" if header["missing_or_error_sources"] else "fresh"},
]
metric_strip(st, metrics, columns=4)
modern_summary_band(
    st,
    title="Map-First Intelligence Layers",
    bullets=[
        f"{len(live_payload['map_layers'])} source-labeled layers with live/proxy/historical truth labels.",
        f"{state['layer_runtime_status']['summary']['row_count']} runtime/static rows represented across layer contracts.",
        f"{len(live_payload['markers']['markers'])} map markers and {len(live_payload['top_hotspots'])} hotspot cards in the current payload.",
        "AISStream, OpenSky, and NASA FIRMS remain missing-key until configured and successfully probed.",
    ],
    keywords=[
        {"label": "map layers", "category": "source freshness", "importance": "high"},
        {"label": "provider gaps", "category": "provider issue", "importance": "high"},
        {"label": "historical-only AIS", "category": "data freshness", "importance": "high"},
    ],
    actions=[
        {"label": "Review source gaps", "description": "Open provider diagnostics for missing keys and probe status.", "command": "DATA PROBE", "page": "pages/17_Data_Provider_Center.py"},
        {"label": "Open Energy Map", "description": "Inspect chokepoints, weather, and energy-linked news.", "command": "CL ENERGY", "page": "pages/9_Energy_Geopolitics.py"},
    ],
)

event_frame = state["event_frame"]
if region_filter != "All" and hasattr(event_frame, "columns") and "region" in event_frame.columns:
    filtered_frame = event_frame[event_frame["region"].astype(str).str.lower().eq(region_filter.lower())]
else:
    filtered_frame = event_frame

map_payload = state["map_payload"]
left, right = st.columns([2.15, 1])

with left:
    terminal_section_header(
        st,
        "Global Event Map",
        "Coordinate-backed events plus clearly marked centroid, static chokepoint, and route exposure proxy layers.",
        badges=[
            severity_badge(header["global_risk_state"]),
            freshness_badge("estimated"),
            status_badge("No live AIS", "unavailable", tone="missing"),
        ],
    )
    fig = map_payload["fig"]
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, key="war_room_layered_event_map")
    else:
        st.info("Map fallback: no coordinate-backed rows available for the selected view.")
        render_table(st, filtered_frame)
    st.caption(map_payload["caveat"])
    legend_cols = st.columns(2)
    with legend_cols[0]:
        st.markdown(
            "".join(
                [
                    severity_badge("critical"),
                    severity_badge("high"),
                    severity_badge("elevated"),
                    severity_badge("watch"),
                    severity_badge("low"),
                ]
            ),
            unsafe_allow_html=True,
        )
    with legend_cols[1]:
        st.markdown(
            "".join(
                [
                    freshness_badge("fresh"),
                    freshness_badge("estimated"),
                    freshness_badge("stale"),
                    freshness_badge("missing"),
                    data_gap_badge("Data gap"),
                ]
            ),
            unsafe_allow_html=True,
        )
    bottom_tabs = st.tabs(["Market Radar", "Stress Bar", "Crypto / Energy Mini", "Event Timeline", "Data Gaps"])
    with bottom_tabs[0]:
        terminal_section_header(st, "Market Radar", "Top linked assets and domains from event linkage; proxy/correlation context only.")
        render_table(st, state["market_impact_summary"]["top_related_assets"])
        render_table(st, state["market_impact_summary"]["domain_mix"])
    with bottom_tabs[1]:
        terminal_section_header(st, "Cross-Asset Stress Bar", "Composite count of related-asset event concentration.")
        st.markdown(mini_bar(state["market_impact_summary"]["stress_bar"], label="Event-linked stress proxy", color="#f59e0b"), unsafe_allow_html=True)
        st.caption(state["market_impact_summary"]["caveat"])
    with bottom_tabs[2]:
        terminal_section_header(st, "Crypto / Energy Mini", "Derivatives and chokepoint panels stay explicit about missing live feeds.")
        c1, c2 = st.columns(2)
        with c1:
            intelligence_card(
                st,
                title="Crypto Derivatives Stress",
                summary="Uses public derivatives context when supplied. Stablecoin flow and exchange solvency feeds are unavailable unless configured.",
                severity="watch",
                tags=["crypto", "proxy"],
                source="crypto derivatives / optional",
                freshness="estimated",
            )
        with c2:
            intelligence_card(
                st,
                title="Energy / Geopolitical Premium",
                summary="Static chokepoints and route exposure arcs are shown as proxies. No live vessel traffic is claimed.",
                severity="watch",
                tags=["energy", "chokepoints"],
                source="static registry",
                freshness="estimated",
            )
    with bottom_tabs[3]:
        render_table(st, state["event_timeline"])
    with bottom_tabs[4]:
        render_table(st, build_data_gap_panel(state))

with right:
    rail_panels = war_room_right_rail_panels({"severity": header["global_risk_state"], "freshness": "estimated", "source_status": "public/proxy"})
    terminal_section_header(st, "War Room Right Rail", "Panel roster with severity, freshness, source status, and data-gap warnings.")
    render_table(st, rail_panels)
    terminal_section_header(st, "Macro / Energy / Chokepoint Rail", "Unified-data ready cards with proxy labels and data gaps.")
    macro_energy = state["macro_energy_payload"]
    render_table(st, macro_energy["macro_cards"])
    render_table(st, macro_energy["energy_cards"])
    render_table(st, macro_energy["chokepoint_cards"])
    terminal_section_header(st, "Source-Labeled Intelligence Feed", "Ranked event cards with source, credibility, freshness, and data-gap caveats.")
    for card in state["right_rail"]["event_cards"][:8]:
        intelligence_card(
            st,
            title=card["title"],
            summary=card["summary"],
            severity=card["severity"],
            tags=card["tags"],
            bullets=card["bullets"],
            source=card["source"],
            freshness=card["freshness"],
        )
    terminal_section_header(st, "AI Brief Context", "Neutral context payload; generate briefs from primary data and verify gaps.")
    ai_context = state["ai_context"]
    intelligence_card(
        st,
        title="AI Brief",
        summary="What changed, related market channels, observed proxy reactions, scenario watch-points, uncertainty, and data gaps.",
        severity="watch",
        tags=["AI summary", "verify primary data", "not financial advice"],
        bullets=ai_context["data_gaps"],
        source="war_room",
        freshness="estimated",
    )
    terminal_section_header(st, "Country / Regional Risk Ranking", "Transparent heuristic scores, not official country risk ratings.")
    render_table(st, state["country_risk_table"])
    terminal_section_header(st, "Hotspot Leaderboard", "Signal convergence across available event rows.")
    render_table(st, state["hotspot_leaderboard"])
    terminal_section_header(st, "Source Status", "Provider status, freshness, missing keys, and optional-feed gaps.")
    render_table(st, state["source_status"])

st.divider()
detail_tabs = st.tabs(["Layers", "Events", "Chokepoints", "Source Freshness", "AI Context"])
with detail_tabs[0]:
    terminal_section_header(st, "Layer Registry", "Unavailable layers are visible as unavailable or optional.")
    layer_payload = layer_control_payload(search=layer_search, domain=layer_domain, time_range=time_range, region=region_filter if region_filter != "All" else "Global")
    st.caption(layer_payload["caveat"])
    terminal_section_header(st, "Layer Runtime Contracts", "JSON-safe layer status with row counts, freshness, caveats, and recommended actions.")
    st.caption(state["layer_runtime_status"]["caveat"])
    render_table(st, state["layer_runtime_status"]["layers"])
    render_table(st, layer_payload["layers"])
    render_table(st, state["layer_status"])
with detail_tabs[1]:
    terminal_section_header(st, "Normalized Event Stream", "Every event follows the War Room schema.")
    render_table(st, filtered_frame)
with detail_tabs[2]:
    choke_fig = map_payload["chokepoint_fig"]
    if choke_fig is not None:
        st.plotly_chart(choke_fig, use_container_width=True, key="war_room_chokepoint_detail_map")
    render_table(st, map_payload["chokepoint_frame"])
    render_status(st, map_payload["chokepoint_status"])
with detail_tabs[3]:
    render_table(st, state["source_status"])
    terminal_section_header(st, "Provider Health Ledger", "Fresh, cached, stale, rate-limited, forbidden, missing-key, unavailable, and proxy/static states.")
    render_table(st, state["provider_health_ledger"]["ledger"])
    terminal_section_header(st, "Goal 10B Layer Quality", "Layer-level freshness, confidence, live/proxy/historical labels, and missing-key report.")
    render_table(st, live_payload["source_freshness"])
    render_table(st, live_payload["missing_keys"])
    render_table(st, region_heatmap["table"])
with detail_tabs[4]:
    st.json({**ai_context, "custom_context": custom_context, "mode": mode})

with st.expander("API Contract Payload Preview", expanded=False):
    terminal_section_header(
        st,
        "War Room Contract",
        "JSON-safe envelope consumed by optional FastAPI routes, static fixtures, and future web clients.",
    )
    war_room_contract = build_api_war_room_payload(state)
    render_table(st, contract_summary_rows(war_room_contract))
    st.json(contract_preview(war_room_contract))

page_footer(st)
