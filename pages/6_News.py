from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.api_contract_panels import contract_preview, contract_summary_rows
from lib.api_contracts import build_api_news_dashboard_payload
from lib.ai_analysis import analyze_energy_geopolitical_neutral
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
from lib.data_status import failure
from lib.catalyst_graph import build_catalyst_cluster_summary, build_catalyst_graph
from lib.event_stream import merge_news_events
from lib.feed_registry import feed_registry_table
from lib.geopolitical_news import build_multi_source_news_feed, build_oil_news_query
from lib.impact_visuals import (
    asset_reaction_bar_chart,
    catalyst_sankey_chart,
    event_asset_heatmap,
    event_timeline_with_market_overlay,
    market_impact_matrix_chart,
    scenario_evidence_contribution_chart,
)
from lib.market_impact_engine import build_event_to_scenario_evidence, build_market_impact_cards, build_news_market_impact_table
import lib.map_viz as map_viz
from lib.news_intelligence import build_worldmonitor_style_news_dashboard
from lib.news_intelligence_dashboard import build_news_dashboard_payload
from lib.overview import build_crypto_mini_panel
from lib.provider_health_engine import build_provider_health_snapshot
from lib.terminal_ui import compact_news_card, intelligence_card, mini_bar, modern_summary_band, provider_health_strip, terminal_page_header, terminal_section_header, terminal_ticker_tape
from lib.ui import page_footer, render_status, render_status_table, render_table
from lib.worldmonitor_adapter import check_worldmonitor_status, get_route_intelligence


def _fallback_chart(name: str, data=None):
    return None, data, failure(source=name, provider="map_viz", error=f"{name} helper unavailable in current Streamlit process.")


def _chokepoint_risk_map(**kwargs):
    builder = getattr(map_viz, "build_chokepoint_risk_map", None)
    if callable(builder):
        return builder(**kwargs)
    return map_viz.build_chokepoint_map()


def _country_news_density_map(news):
    builder = getattr(map_viz, "build_country_news_density_map", None)
    if callable(builder):
        return builder(news)
    return map_viz.build_country_risk_map()


build_energy_route_proxy_map = getattr(map_viz, "build_energy_route_proxy_map", map_viz.build_energy_route_map_proxy)
build_event_timeline_chart = getattr(map_viz, "build_event_timeline_chart", lambda timeline=None: _fallback_chart("event timeline chart", timeline))
build_news_severity_bar = getattr(map_viz, "build_news_severity_bar", lambda items=None: _fallback_chart("news severity bar", items))
build_source_freshness_chart = getattr(map_viz, "build_source_freshness_chart", lambda statuses=None: _fallback_chart("source freshness chart", statuses))
build_terminal_event_map = getattr(map_viz, "build_terminal_event_map", map_viz.build_event_map)


@st.cache_data(ttl=300, show_spinner=False)
def _load_news_feed(query_text: str):
    return build_multi_source_news_feed(query_text)


st.set_page_config(page_title="News Intelligence", layout="wide")
terminal_page_header(
    st,
    "News Intelligence",
    "WorldMonitor-style public feed clustering, market impact, maps, source freshness, and neutral AI briefs.",
    meta=[
        {"label": "Classification", "value": "heuristic", "tone": "estimated"},
        {"label": "Live AIS", "value": "unavailable", "tone": "missing"},
        {"label": "Runtime boundary", "value": "no external WorldMonitor imports", "tone": "fresh"},
    ],
)
provider_health_strip(st)

with st.sidebar:
    query = st.text_input("News query", build_oil_news_query())
    provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
    preferred_provider = st.selectbox("AI provider", provider_names, index=0)
    use_local = st.checkbox("Use local Ollama if available", value=False)
    show_prompt_context = st.checkbox("Show prompt context", value=False)
    fetch_market_reactions = st.checkbox("Fetch related market reactions", value=False)
    refresh_news = st.button("Refresh public feeds", key="news_refresh")
    route_from = st.text_input("Route from ISO2", "US")
    route_to = st.text_input("Route to ISO2", "KR")

selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider
if refresh_news:
    _load_news_feed.clear()
payload, status = _load_news_feed(query)
statuses = [status] + list(payload.get("source_status", []) or [])
dashboard = build_worldmonitor_style_news_dashboard(payload.get("news"), statuses)
provider_health = build_provider_health_snapshot(statuses)
news = dashboard["normalized_news"]
goal10b_news = build_news_dashboard_payload(payload.get("news"), [status.to_dict() if hasattr(status, "to_dict") else status for status in statuses])

tabs = st.tabs(
    [
        "Command Feed",
        "Market Impact",
        "Catalyst Graph",
        "Geopolitical Map",
        "Oil / Chokepoints",
        "Crypto / Risk",
        "Source Freshness",
        "AI Brief",
        "WorldMonitor Adapter",
    ]
)


def _records(frame, limit: int = 20):
    if frame is None or getattr(frame, "empty", True):
        return []
    return frame.head(limit).to_dict(orient="records")


def _channel_filter(frame, channel: str):
    if frame is None or getattr(frame, "empty", True) or "impact_channels" not in frame.columns:
        return pd.DataFrame()
    return frame[frame["impact_channels"].apply(lambda values: channel in values if isinstance(values, list) else channel in str(values).lower())]


with tabs[0]:
    terminal_section_header(st, "Command Feed", "Compact cards with severity, region, asset channel, credibility, and freshness.")
    render_status(st, status)
    modern_summary_band(
        st,
        title="News Intelligence Dashboard",
        bullets=[
            f"{len(goal10b_news['timeline'])} deduplicated events with theme, region, and asset filters.",
            f"Themes: {', '.join(goal10b_news['theme_filters'][:6]) or 'none'}",
            goal10b_news["duplicate_cluster_note"],
        ],
        keywords=[
            {"label": "event timeline", "category": "risk driver", "importance": "medium"},
            {"label": "source freshness", "category": "data freshness", "importance": "high"},
            {"label": "asset links", "category": "asset affected", "importance": "medium"},
        ],
        actions=[
            {"label": "Open War Room", "description": "Inspect map-linked news events and provider gaps.", "command": "WR", "page": "pages/14_War_Room.py"},
            {"label": "Verify news sources", "description": "Review GDELT, NWS, USGS, and optional OSINT source probes.", "command": "DATA PROBE news", "page": "pages/17_Data_Provider_Center.py"},
        ],
    )
    high_feed = dashboard["high_severity_feed"]
    if high_feed is not None and not getattr(high_feed, "empty", True):
        st.markdown(
            terminal_ticker_tape(
                [
                    {"label": row.get("severity", "watch"), "value": row.get("region", "Global"), "delta": row.get("source", "feed"), "freshness": row.get("freshness", "estimated")}
                    for row in high_feed.head(10).to_dict(orient="records")
                ]
            )["html"],
            unsafe_allow_html=True,
        )
    if high_feed is None or getattr(high_feed, "empty", True):
        st.info("No public news rows are currently available. Source status below explains the gap.")
    for item in _records(high_feed, 18):
        compact_news_card(st, item)
        if item.get("url"):
            st.link_button("Open source", item["url"])
    with st.expander("Normalized feed rows", expanded=False):
        render_table(st, news)

with tabs[1]:
    terminal_section_header(st, "Market Impact", "News/event clusters mapped to related assets, potential channels, and observed proxy reactions.")
    news_events = merge_news_events(news)
    impact_table, impact_status = build_news_market_impact_table(news_events, fetch_market_data=fetch_market_reactions)
    impact_cols = st.columns([1.2, 1])
    with impact_cols[0]:
        impact_fig, impact_frame, impact_fig_status = market_impact_matrix_chart(impact_table)
        if impact_fig is not None:
            st.plotly_chart(impact_fig, use_container_width=True, key="news_market_impact_matrix")
        else:
            render_table(st, dashboard["impact_matrix"])
        render_status(st, impact_fig_status)
    with impact_cols[1]:
        severity_fig, severity_frame, severity_status = build_news_severity_bar(news)
        if severity_fig is not None:
            st.plotly_chart(severity_fig, use_container_width=True, key="news_market_severity_bar")
        else:
            render_table(st, severity_frame)
        render_status(st, severity_status)
    reaction_fig, reaction_frame, reaction_status = asset_reaction_bar_chart(impact_table)
    if reaction_fig is not None:
        st.plotly_chart(reaction_fig, use_container_width=True, key="news_market_asset_reaction")
    else:
        render_table(st, reaction_frame)
    render_status(st, reaction_status)
    timeline_fig, timeline_frame, timeline_status = event_timeline_with_market_overlay(news_events, impact_table)
    if timeline_fig is not None:
        st.plotly_chart(timeline_fig, use_container_width=True, key="news_market_timeline_overlay")
    else:
        render_table(st, timeline_frame)
    render_status(st, timeline_status)
    render_status(st, impact_status)
    terminal_section_header(st, "High-Impact Event Cards", "Potential channel and proxy/correlation context. No causal attribution is asserted.")
    for card in build_market_impact_cards(news_events, impact_table, limit=8):
        intelligence_card(st, title=card["title"], summary=card["summary"], severity=card["severity"], tags=card["tags"], bullets=card["bullets"], source=card["source"], freshness=card["freshness"])
    with st.expander("Impact table", expanded=False):
        render_table(st, impact_table)
    scenario_evidence = build_event_to_scenario_evidence(news_events, impact_table)
    evidence_fig, evidence_frame, evidence_status = scenario_evidence_contribution_chart(scenario_evidence)
    if evidence_fig is not None:
        st.plotly_chart(evidence_fig, use_container_width=True, key="news_market_scenario_evidence")
    else:
        render_table(st, evidence_frame)
    render_status(st, evidence_status)

with tabs[2]:
    terminal_section_header(st, "Catalyst Graph", "Event -> region -> asset -> scenario relation view with edge-table fallback.")
    news_events = merge_news_events(news)
    impact_table, impact_status = build_news_market_impact_table(news_events, fetch_market_data=fetch_market_reactions)
    graph = build_catalyst_graph(news_events, impact_table)
    sankey_fig, sankey_frame, sankey_status = catalyst_sankey_chart(graph)
    if sankey_fig is not None:
        st.plotly_chart(sankey_fig, use_container_width=True, key="news_catalyst_sankey")
    else:
        render_table(st, sankey_frame)
    render_status(st, sankey_status)
    heatmap_fig, heatmap_frame, heatmap_status = event_asset_heatmap(impact_table)
    if heatmap_fig is not None:
        st.plotly_chart(heatmap_fig, use_container_width=True, key="news_catalyst_event_asset_heatmap")
    else:
        render_table(st, heatmap_frame)
    render_status(st, heatmap_status)
    cluster_summary = build_catalyst_cluster_summary(news_events, graph)
    render_table(st, cluster_summary)
    with st.expander("Graph nodes", expanded=False):
        render_table(st, graph["nodes"])
    with st.expander("Graph edges", expanded=False):
        render_table(st, graph["edges"])
    render_status(st, impact_status)

with tabs[3]:
    terminal_section_header(st, "Geopolitical Map", "Coordinate-backed events render on map; otherwise regional cards stay visible.")
    event_fig, event_frame, event_status = build_terminal_event_map(dashboard["event_rows"])
    if event_fig is not None:
        st.plotly_chart(event_fig, use_container_width=True, key="news_geo_event_map")
    else:
        country_fig, country_frame, country_status = _country_news_density_map(news)
        if country_fig is not None:
            st.plotly_chart(country_fig, use_container_width=True, key="news_geo_country_density")
        else:
            render_table(st, dashboard["regional_cards"])
        render_status(st, country_status)
    render_status(st, event_status)
    card_cols = st.columns(3)
    for idx, row in enumerate(_records(dashboard["regional_cards"], 9)):
        with card_cols[idx % 3]:
            intelligence_card(
                st,
                title=str(row.get("region", "Region")),
                summary=f"{row.get('headline_count', 0)} headlines; {row.get('impact_channels', 'unclassified')} channels.",
                severity=str(row.get("severity", "watch")),
                tags=["regional", "heuristic"],
                source=row.get("method"),
                freshness="estimated",
            )
    terminal_section_header(st, "Goal 10B Event Map Preview", "Only events with sufficient coordinate confidence appear as map-preview rows.")
    render_table(st, pd.DataFrame(goal10b_news["event_map_preview"]))

with tabs[4]:
    terminal_section_header(st, "Oil / Chokepoints", "Static chokepoint registry plus public headline proximity. No live vessel flow is claimed.")
    oil_news = pd.concat([_channel_filter(news, "oil"), _channel_filter(news, "shipping")], ignore_index=True).drop_duplicates(subset=["title"]) if news is not None and not getattr(news, "empty", True) else pd.DataFrame()
    map_cols = st.columns([1.25, 1])
    with map_cols[0]:
        choke_fig, choke_frame, choke_status = _chokepoint_risk_map(news_items=oil_news)
        if choke_fig is not None:
            st.plotly_chart(choke_fig, use_container_width=True, key="news_oil_chokepoint_map")
        else:
            render_table(st, choke_frame)
        render_status(st, choke_status)
    with map_cols[1]:
        route_fig, routes, route_status = build_energy_route_proxy_map()
        if route_fig is not None:
            st.plotly_chart(route_fig, use_container_width=True, key="news_oil_route_proxy")
        else:
            st.json(routes)
        render_status(st, route_status)
    st.warning("AIS unavailable warning: this app does not claim live vessel tracking without a real AIS provider.")
    render_table(st, oil_news[["title", "severity", "source", "freshness", "related_assets"]] if not getattr(oil_news, "empty", True) else oil_news)

with tabs[5]:
    terminal_section_header(st, "Crypto / Risk", "Crypto regulatory, security, liquidation, and macro-risk headlines with market context.")
    crypto_news = _channel_filter(news, "crypto")
    risk_news = news[news["severity"].isin(["critical", "high", "medium"])] if news is not None and not getattr(news, "empty", True) else pd.DataFrame()
    crypto_panel, crypto_status = build_crypto_mini_panel()
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("BTC", "N/A" if crypto_panel.get("btc_price") is None else f"{crypto_panel.get('btc_price'):,.2f}")
    with metric_cols[1]:
        st.metric("Funding", "N/A")
    with metric_cols[2]:
        st.metric("Long/short ratio", "N/A")
    with metric_cols[3]:
        st.metric("Liquidation pressure", crypto_panel.get("liquidation_pressure_summary", "data gap"))
    render_status(st, crypto_status)
    for item in _records(pd.concat([crypto_news, risk_news], ignore_index=True).drop_duplicates(subset=["title"]), 12):
        compact_news_card(st, item)

with tabs[6]:
    terminal_section_header(st, "Source Freshness", "Fetch state, feed counts, stale/missing status, and errors.")
    freshness_fig, freshness_frame, freshness_status = build_source_freshness_chart(dashboard["source_freshness"])
    if freshness_fig is not None:
        st.plotly_chart(freshness_fig, use_container_width=True, key="news_source_freshness")
    render_table(st, dashboard["source_freshness"])
    terminal_section_header(st, "Curated Feed Registry", "Default-enabled public feeds, optional feeds, source tier, risk, and caveats.")
    render_table(st, pd.DataFrame(feed_registry_table()))
    terminal_section_header(st, "Provider Health Ledger", "Partial failures stay visible as rate-limited, forbidden, missing-key, unavailable, or stale.")
    render_table(st, provider_health["ledger"])
    terminal_section_header(st, "Goal 10B Theme Heatmap And Filters", "News heatmap uses internal event rows and source-labeled theme classification.")
    render_table(st, goal10b_news["heatmap"]["table"])
    render_table(st, pd.DataFrame(goal10b_news["source_freshness"]))
    render_status(st, freshness_status)

with tabs[7]:
    terminal_section_header(st, "AI Brief", "Neutral, button-triggered brief with market impact context.")
    news_events = merge_news_events(news)
    impact_table, impact_status = build_news_market_impact_table(news_events, fetch_market_data=False)
    scenario_evidence = build_event_to_scenario_evidence(news_events, impact_table)
    st.caption(f"Provider: {select_ai_provider(selected_ai).provider} | Model: {select_ai_provider(selected_ai).model}")
    context = {
        "what_changed": dashboard["high_severity_feed"].head(12).to_dict(orient="records") if hasattr(dashboard["high_severity_feed"], "head") else [],
        "related_market_channels": impact_table.head(20).to_dict(orient="records") if hasattr(impact_table, "head") else [],
        "observed_proxy_reactions": impact_table[["ticker", "impact_label", "latest_return_pct", "return_1d_pct", "data_gap"]].head(20).to_dict(orient="records") if hasattr(impact_table, "columns") and "ticker" in impact_table.columns else [],
        "scenario_watch_points": scenario_evidence.head(12).to_dict(orient="records") if hasattr(scenario_evidence, "head") else [],
        "watch_points": dashboard["risk_catalysts"][:8],
        "uncertainty": "Public feeds can be delayed, rate-limited, duplicated, or missing coordinates.",
        "data_gaps": dashboard["notes"],
        "source_freshness": dashboard["source_freshness"].to_dict(orient="records") if hasattr(dashboard["source_freshness"], "to_dict") else [],
    }
    if show_prompt_context:
        with st.expander("Prompt context", expanded=False):
            st.json(redact_secrets(str(context)))
    if st.button("Generate neutral AI digest", key="news_ai"):
        response = analyze_energy_geopolitical_neutral(context, preferred=selected_ai)
        st.markdown(response.text)
        st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")

with tabs[8]:
    terminal_section_header(st, "WorldMonitor Adapter", "Optional external API boundary. Reference-only source tree is not imported at runtime.")
    wm_status = check_worldmonitor_status()
    render_status_table(st, [wm_status])
    st.caption("WorldMonitor is optional. Private or pro-gated surfaces are not scraped, and AGPL source is not copied into runtime modules.")
    if st.button("Check optional route intelligence", key="wm_route"):
        route_status = get_route_intelligence(route_from.upper(), route_to.upper())
        render_status_table(st, [route_status])
        if route_status.ok:
            st.json(route_status.data)
        else:
            st.warning(route_status.error or "Route intelligence unavailable.")

with st.expander("Raw Source Status", expanded=False):
    render_status_table(st, statuses)

with st.expander("API Contract Payload Preview", expanded=False):
    terminal_section_header(
        st,
        "News Contract",
        "JSON-safe news dashboard envelope for optional FastAPI routes, static fixtures, and future web clients.",
    )
    news_contract = build_api_news_dashboard_payload(dashboard=dashboard)
    render_table(st, contract_summary_rows(news_contract))
    st.json(contract_preview(news_contract))

page_footer(st)
