from __future__ import annotations

import streamlit as st

from lib.alert_evaluator import evaluate_all_alerts
from lib.command_palette_ui import build_command_palette_state, run_command_palette_action
from lib.watchlist_models import infer_item_type
from lib.watchlist_store import create_watchlist_item
from lib.research_workflow_actions import run_research_workflow_action
from lib.streamlit_research_renderers import render_action_cards, render_chip_strip
from lib.watchlist_page_layout import build_watchlist_page_payload
from lib.watchlist_tradingview_widgets import build_watchlist_market_quotes_widget, build_watchlist_tradingview_disclaimer

st.set_page_config(page_title="Watchlist & Alerts", layout="wide")
st.title("Watchlist & Alert Center")
st.caption("Research and monitoring workspace only. Values, alerts, and reports must retain source/freshness/confidence caveats.")

payload = build_watchlist_page_payload()

st.subheader("Summary")
summary_cols = st.columns(3)
for idx, metric in enumerate(payload["summary_strip"]):
    with summary_cols[idx % 3]:
        st.metric(metric["label"], metric["value"])

st.subheader("Source freshness")
chip_cols = st.columns(max(1, min(4, len(payload["source_freshness"]["chips"]))))
for idx, chip in enumerate(payload["source_freshness"]["chips"]):
    with chip_cols[idx % len(chip_cols)]:
        st.info(f"{chip['source']} · {chip['status']} · {chip['confidence']}")

with st.expander("Quick add / command search", expanded=True):
    query = st.text_input("Search or add", value="BTCUSDT", placeholder="AAPL, BTCUSDT, Red Sea, FRED, Strategy Ensemble #3")
    state = build_command_palette_state(query)
    for idx, card in enumerate(state["result_cards"]):
        with st.container(border=True):
            st.markdown(f"**{card['title']}**")
            st.caption(card.get("caveat", ""))
            if card.get("safe_alternatives"):
                st.caption("Safe alternatives: " + "; ".join(a["label"] for a in card["safe_alternatives"]))
            if card.get("enabled") and st.button(f"Run command action {idx + 1}", key=f"watch_cmd_{idx}"):
                st.json(run_command_palette_action(state["suggestions"][idx], query=query), expanded=False)
    with st.form("add_watchlist_item"):
        value = st.text_input("Symbol, region, chokepoint, provider, strategy, or topic", value=query)
        reason = st.text_input("Watch reason", value="Research monitoring")
        submitted = st.form_submit_button("Add watchlist item")
        if submitted:
            result = run_research_workflow_action("ADD_WATCHLIST_ITEM", {"query": value, "watch_reason": reason})
            if result.get("ok"):
                st.success(f"Added {result['item']['display_name']}")
            else:
                st.error(result.get("error", "Action failed"))

tab_table, tab_detail, tab_events, tab_alerts, tab_context, tab_tv, tab_raw = st.tabs(["Watchlist", "Detail", "News/Event Grid", "Alerts", "RMI / volatility / heatmap", "TradingView supplement", "Raw payload"])
with tab_table:
    for card in payload["action_cards"]:
        with st.container(border=True):
            st.markdown(f"**{card['title']}**")
            st.caption(card["summary"])
            st.code(card["command"])
    if payload["empty_states"]["no_watchlist_items"]:
        st.info("No watchlist items yet.")
    st.dataframe(payload["product_table"], use_container_width=True)
with tab_detail:
    detail = payload["detail_panel"]
    if detail.get("empty"):
        st.info(detail["message"])
    else:
        st.markdown(f"### {detail['title']}")
        st.caption(detail["summary"])
        st.dataframe(detail["badges"], use_container_width=True)
        st.write("Provider caveats")
        st.dataframe(detail["provider_caveats"].get("chips", []), use_container_width=True)
with tab_events:
    grid = payload["news_event_grid"]
    if grid["empty"]:
        st.info(grid["empty_message"])
    st.dataframe(grid["rows"], use_container_width=True)
with tab_alerts:
    st.dataframe([payload["alert_builder"]], use_container_width=True)
    if st.button("Evaluate alerts now"):
        st.dataframe(evaluate_all_alerts({}), use_container_width=True)
    st.dataframe(payload["alert_cards"], use_container_width=True)
    st.dataframe(payload["alert_timeline"], use_container_width=True)
with tab_context:
    st.subheader("Heatmap")
    st.write(payload["heatmap"].get("title", "Watchlist Heatmap"))
    st.dataframe(payload["heatmap"].get("tiles", payload["heatmap"].get("rows", [])), use_container_width=True)
    st.subheader("Relative Market Intelligence")
    st.dataframe(payload["rmi"].get("rows", []), use_container_width=True)
    st.subheader("Volatility")
    st.dataframe(payload["volatility"].get("rows", []), use_container_width=True)
with tab_tv:
    st.caption(build_watchlist_tradingview_disclaimer()["text"])
    symbols = [row.get("symbol") for row in payload["table"] if row.get("symbol")]
    st.json(build_watchlist_market_quotes_widget(symbols, enabled=False), expanded=False)
with tab_raw:
    with st.expander("Raw payload"):
        st.json(payload, expanded=False)
