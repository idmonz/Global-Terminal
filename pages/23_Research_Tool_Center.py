from __future__ import annotations

import streamlit as st

from lib.research_tool_center import build_research_tool_center_payload
from lib.research_tool_actions import run_research_tool_action, search_research_tools
from lib.streamlit_research_renderers import render_tool_cards

st.set_page_config(page_title="Research Tool Center", layout="wide")
st.title("Research Tool Center")
st.caption("Manual research tools, diagnostics, exports, and review workflows. No execution actions are provided.")

payload = build_research_tool_center_payload()
st.metric("Tools", payload["tool_count"])
query = st.text_input("Search tools", value="")
matching_tools = search_research_tools(query)
render_tool_cards(matching_tools, st=None)
for section in payload["sections"]:
    st.subheader(section["section"])
    cols = st.columns(3)
    for idx, tool in enumerate(section["tools"]):
        with cols[idx % 3]:
            st.markdown(f"**{tool['tool_name']}**")
            st.caption(tool["purpose"])
            st.code(tool["command"])
            st.caption(f"Data: {tool['data_required']} | Output: {tool['output_type']}")
            st.info(tool["caveat"])
            if st.button(f"Run safe workflow: {tool['tool_name']}", key=f"tool_{tool['tool_name']}"):
                st.json(run_research_tool_action(tool["tool_name"]), expanded=False)
with st.expander("Raw payload"):
    st.json(payload, expanded=False)
