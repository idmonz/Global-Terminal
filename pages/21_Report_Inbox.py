from __future__ import annotations

import streamlit as st

from lib.headless_report_runner import run_report_generator
from lib.report_inbox_page_layout import build_report_inbox_page_payload
from lib.report_review_workflow import update_report_review_status
from lib.report_reader_workflow import build_report_reader_workflow_state, update_selected_report_review
from lib.streamlit_research_renderers import render_report_sidebar, render_report_reader, render_action_cards
from lib.research_session_state import get_research_session_state, persist_last_action_result, persist_report_filter_state

st.set_page_config(page_title="Report Inbox", layout="wide")
st.title("Report Inbox")
st.caption("Reports are source-labeled research artifacts. Verify freshness, provider gaps, and caveats before using them in a workflow.")

session_state = get_research_session_state(st.session_state)
base_payload = build_report_inbox_page_payload()
with st.sidebar:
    st.subheader("Filters")
    saved_filters = session_state.get("report_filters", {"report_type": "all", "review_status": "all", "query": ""})
    q = st.text_input("Search", value=saved_filters.get("query", ""))
    rtype = st.selectbox("Report type", base_payload["filter_state"]["available_types"], index=base_payload["filter_state"]["available_types"].index(saved_filters.get("report_type", "all")) if saved_filters.get("report_type", "all") in base_payload["filter_state"]["available_types"] else 0)
    rstatus = st.selectbox("Review status", base_payload["filter_state"]["review_states"], index=base_payload["filter_state"]["review_states"].index(saved_filters.get("review_status", "all")) if saved_filters.get("review_status", "all") in base_payload["filter_state"]["review_states"] else 0)
    persist_report_filter_state(report_type=rtype, review_status=rstatus, query=q, session_state=session_state)

payload = build_report_inbox_page_payload(query=q, report_type=rtype, review_status=rstatus)
workflow_state = build_report_reader_workflow_state(selected_report_id=session_state.get("selected_report_id"), report_type=rtype, review_status=rstatus, query=q, session_state=session_state)
choice = st.selectbox("Manual report generator", payload["generators"])
if st.button("Generate selected report"):
    report = run_report_generator(choice)
    st.success(report["title"])
    persist_last_action_result({"action": "GENERATE_REPORT", "report_id": report.get("report_id"), "ok": True, "research_only": True}, session_state=session_state)
    session_state["selected_report_id"] = report.get("report_id", session_state.get("selected_report_id", ""))
    payload = build_report_inbox_page_payload(query=q, report_type=rtype, review_status=rstatus)
workflow_state = build_report_reader_workflow_state(selected_report_id=session_state.get("selected_report_id"), report_type=rtype, review_status=rstatus, query=q, session_state=session_state)

tab_list, tab_reader, tab_review, tab_sources, tab_export, tab_raw = st.tabs(["Reports", "Reader", "Review", "Sources", "Export", "Raw payload"])
with tab_list:
    if payload["empty_states"]["no_reports"]:
        st.info("No reports yet. Generate a manual brief from the selector above.")
    render_report_sidebar(workflow_state["sidebar"], st=st)
    st.dataframe(payload["cards"], use_container_width=True)
with tab_reader:
    reader = workflow_state["reader"]
    if reader.get("empty"):
        st.info(reader["message"])
    else:
        st.markdown(f"## {reader['title']}")
        st.caption(reader["summary"])
        render_report_reader(reader, st=st)
with tab_review:
    st.write("Review workflow")
    st.json(payload["review_workflow"], expanded=False)
    latest = workflow_state.get("selected_report") or payload.get("latest") or {}
    note = st.text_area("Review note", value=latest.get("review_notes", ""))
    cols = st.columns(3)
    if latest:
        with cols[0]:
            if st.button("Mark reviewed"):
                st.success(update_selected_report_review(latest["report_id"], "reviewed", notes=note, session_state=session_state)["to"])
        with cols[1]:
            if st.button("Flag for review"):
                st.warning(update_selected_report_review(latest["report_id"], "requires_review", notes=note, session_state=session_state)["to"])
        with cols[2]:
            if st.button("Archive"):
                st.info(update_selected_report_review(latest["report_id"], "archived", notes=note, session_state=session_state)["to"])
    st.dataframe(payload["action_cards"], use_container_width=True)
with tab_sources:
    st.subheader("Source snapshot / provider gaps")
    st.json((workflow_state.get("selected_report") or {}).get("source_snapshot_json", {}), expanded=False)
    st.dataframe(workflow_state["source_caveat_panel"].get("provider_caveats", {}).get("chips", []), use_container_width=True)
with tab_export:
    st.write("Export buttons are local/manual. Private exports are excluded from release packages.")
    st.dataframe([card for card in payload["action_cards"] if "EXPORT" in card.get("command", "")], use_container_width=True)
with tab_raw:
    with st.expander("Raw payload"):
        st.json(payload, expanded=False)
