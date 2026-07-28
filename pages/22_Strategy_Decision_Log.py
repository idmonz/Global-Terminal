from __future__ import annotations

import streamlit as st

from lib.strategy_decision_log import create_strategy_commit
from lib.strategy_log_page_layout import build_strategy_log_page_payload
from lib.strategy_review_workflow import update_strategy_review_status
from lib.strategy_review_actions import build_selected_strategy_payload, update_selected_strategy_review
from lib.streamlit_research_renderers import render_strategy_review_queue
from lib.research_session_state import get_research_session_state, persist_last_action_result

st.set_page_config(page_title="Strategy Decision Log", layout="wide")
st.title("Strategy-as-Git Decision Log")
st.caption("Strategy commits are research records with guard review, source caveats, and artifact history. They are not execution approvals or market-direction guidance.")
session_state = get_research_session_state(st.session_state)

with st.form("strategy_commit"):
    strategy_id = st.text_input("Strategy candidate ID", value="strategy_candidate")
    message = st.text_area("Research commit message", value="Record why this candidate requires review.")
    submitted = st.form_submit_button("Create research commit")
    if submitted:
        commit = create_strategy_commit(strategy_id=strategy_id, message=message)
        session_state["selected_strategy_commit_id"] = commit["commit_id"]
        persist_last_action_result({"action": "CREATE_STRATEGY_COMMIT", "commit_id": commit["commit_id"], "ok": True, "research_only": True}, session_state=session_state)
        st.success(f"Created {commit['commit_id']}")

payload = build_strategy_log_page_payload()
selected_payload = build_selected_strategy_payload(session_state=session_state)
tab_queue, tab_reader, tab_guards, tab_graph, tab_artifacts, tab_raw = st.tabs(["Review queue", "Commit reader", "Guard dashboard", "Commit graph / diff", "Artifact timeline", "Raw payload"])
with tab_queue:
    if payload["empty_states"]["no_strategy_commits"]:
        st.info("No strategy commits yet.")
    render_strategy_review_queue(selected_payload, st=st)
    st.json(selected_payload["review_workflow"], expanded=False)
    reader = selected_payload.get("commit_reader", {})
    if reader.get("commit_id"):
        note = st.text_area("Review note", value="")
        cols = st.columns(3)
        with cols[0]:
            if st.button("Mark reviewed"):
                st.success(update_selected_strategy_review(reader["commit_id"], "reviewed", note=note, session_state=session_state)["to"])
        with cols[1]:
            if st.button("Flag for review"):
                st.warning(update_selected_strategy_review(reader["commit_id"], "requires_review", note=note, session_state=session_state)["to"])
        with cols[2]:
            if st.button("Archive"):
                st.info(update_selected_strategy_review(reader["commit_id"], "archived", note=note, session_state=session_state)["to"])
with tab_reader:
    reader = selected_payload["commit_reader"]
    if reader.get("empty"):
        st.info(reader["message"])
    else:
        st.markdown(f"### {reader['strategy_id']} / {reader['commit_id']}")
        st.write(reader["message"])
        st.dataframe(reader["guard_cards"], use_container_width=True)
with tab_guards:
    st.json(selected_payload["guard_dashboard"], expanded=False)
    st.dataframe(payload["latest_guard_cards"], use_container_width=True)
with tab_graph:
    st.dataframe(payload["graph_table"], use_container_width=True)
    st.json(selected_payload["diff_panel"], expanded=False)
with tab_artifacts:
    st.json(payload["forward_tracking_panel"], expanded=False)
    st.dataframe(selected_payload["artifact_timeline"].get("events", []), use_container_width=True)
    st.json(payload["linked_context"], expanded=False)
with tab_raw:
    with st.expander("Raw payload"):
        st.json(payload, expanded=False)
