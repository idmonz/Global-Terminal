from __future__ import annotations

import streamlit as st

from lib.workspace_page_layout import build_workspace_page_payload
from lib.workspace_quick_actions import run_quick_action
from lib.command_palette_ui import build_command_palette_state, run_command_palette_action
from lib.streamlit_research_renderers import render_action_cards, render_chip_strip, render_intel_feed, render_tool_cards

st.set_page_config(page_title="Research Workspace", layout="wide")
st.title("Personal Research Operating System")
st.caption("Research and monitoring workspace only. It provides source-labeled context, not market-direction guidance or execution instructions.")

payload = build_workspace_page_payload()
cols = st.columns(4)
for idx, card in enumerate(payload["cards"]):
    with cols[idx % 4]:
        st.metric(card["title"], card["value"])

st.subheader("Source freshness")
chip_cols = st.columns(max(1, min(4, len(payload["source_freshness"]["chips"]))))
for idx, chip in enumerate(payload["source_freshness"]["chips"]):
    with chip_cols[idx % len(chip_cols)]:
        st.info(f"{chip['source']} · {chip['status']} · {chip['confidence']}")

tab_home, tab_command, tab_feed, tab_activity, tab_raw = st.tabs(["Home", "Command palette", "Intel / alerts", "Activity", "Raw payload"])
with tab_home:
    st.subheader("What requires review")
    if payload["requires_review"]:
        for item in payload["requires_review"]:
            st.warning(item)
    else:
        st.success("No local workspace review item is currently flagged.")
    st.subheader("Navigation cards")
    for card in payload["nav_cards"]:
        with st.container(border=True):
            st.markdown(f"**{card['label']}**")
            st.caption(card["purpose"])
            st.code(card["command"])
    if payload["empty_states"].get("no_watchlist_items"):
        st.info("No watchlist items yet. Add an asset, provider, region, chokepoint, strategy, or report topic from Watchlist & Alerts.")
with tab_command:
    state = payload["command_palette"]
    query = st.text_input("Command/search", value=state["query"], placeholder=state["placeholder"])
    if query != state["query"]:
        state = build_command_palette_state(query)
    st.write("Resolved object", state["resolved_object"])
    render_command_payload = render_action_cards(state["result_cards"], st=None)
    for idx, card in enumerate(render_command_payload["cards"]):
        with st.container(border=True):
            st.markdown(f"**{card['title']}**")
            st.caption(f"Command: {card['command']} | Page: {card['page']}")
            if card.get("safe_alternatives"):
                st.caption("Safe alternatives: " + "; ".join(a["label"] for a in card["safe_alternatives"]))
            if card.get("enabled") and st.button(f"Run safe action {idx + 1}", key=f"workspace_cmd_{idx}"):
                st.json(run_command_palette_action(state["suggestions"][idx], query=query), expanded=False)
    st.subheader("Manual quick actions")
    for action in payload["quick_actions"]:
        st.write(f"**{action['label']}** — `{action['code']}`")
    if st.button("Generate Watchlist Brief"):
        st.success(run_quick_action("GENERATE WATCHLIST BRIEF")["result"]["title"])
with tab_feed:
    st.subheader("View presets")
    render_tool_cards({"tools": payload["view_presets"]["presets"]}, st=None)
    st.dataframe(payload["view_presets"]["presets"], use_container_width=True)
    st.subheader("Layer panel")
    render_tool_cards({"tools": payload["layer_panel"]["layers"]}, st=None)
    st.dataframe(payload["layer_panel"]["layers"], use_container_width=True)
    st.subheader("Intel Feed")
    if payload["intel_feed"]["empty"]:
        st.info(payload["intel_feed"]["empty_message"])
    else:
        st.dataframe(payload["intel_feed"]["rows"], use_container_width=True)
    st.subheader("Live Alerts")
    if payload["live_alerts"]["empty"]:
        st.info(payload["live_alerts"]["empty_message"])
    else:
        st.dataframe(payload["live_alerts"]["rows"], use_container_width=True)
    st.subheader("Hotspots")
    st.dataframe(payload["hotspot_panel"]["rows"], use_container_width=True)
with tab_activity:
    st.write("Recent reports")
    st.dataframe(payload["summary"].get("recent_reports", []), use_container_width=True)
    st.write("Recent strategy commits")
    st.dataframe(payload["summary"].get("recent_strategy_commits", []), use_container_width=True)
    st.write("Activity transcript")
    st.dataframe(payload.get("activity_transcript", []), use_container_width=True)
with tab_raw:
    with st.expander("Raw payload"):
        st.json(payload, expanded=False)
