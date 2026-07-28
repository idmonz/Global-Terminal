from __future__ import annotations

import streamlit as st

from lib.ai_analysis import analyze_overview_neutral
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
from lib.macro import build_unified_macro_dashboard, get_macro_dashboard
from lib.terminal_ui import goal10_summary_strip, terminal_page_header
from lib.ui import page_footer, render_status, render_table


st.set_page_config(page_title="Macro", layout="wide")
terminal_page_header(
    st,
    "Macro",
    "Macro dashboard, unified rates backend, source status, and neutral AI context.",
    meta=[
        {"label": "Mode", "value": "research", "tone": "info"},
        {"label": "Providers", "value": "FRED/EIA optional", "tone": "estimated"},
    ],
)
goal10_summary_strip(st, workspace="Macro", risk_state="watch", data_confidence="provider-labeled", provider_status="optional keys visible")

provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
preferred_provider = st.sidebar.selectbox("AI provider", provider_names, index=0)
use_local = st.sidebar.checkbox("Use local Ollama if available", value=False)
show_prompt_context = st.sidebar.checkbox("Show prompt context", value=False)
selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider
source_mode = st.sidebar.selectbox("Data source mode", ["auto", "native_only", "openbb_preferred", "openbb_only"], index=0)

data, status = get_macro_dashboard()
unified_payload = build_unified_macro_dashboard(source_mode=source_mode)
tabs = st.tabs(["Dashboard", "Unified Macro / Rates", "AI"])

with tabs[0]:
    render_status(st, status)
    render_table(st, data)

with tabs[1]:
    st.subheader("Unified Macro / Rates Backend")
    st.caption(unified_payload["caveat"])
    render_table(st, unified_payload["status_table"])
    render_table(st, unified_payload["regime_cards"])
    rate_result = unified_payload["results"]["treasury_curve"]
    st.caption(f"Rates route: {rate_result.provider} | freshness: {rate_result.freshness}")
    render_table(st, rate_result.data)

with tabs[2]:
    st.caption(f"Provider: {select_ai_provider(selected_ai).provider} | Model: {select_ai_provider(selected_ai).model}")
    context = {
        "macro_dashboard": data.head(30).to_dict(orient="records") if hasattr(data, "head") else data,
        "unified_macro_status": unified_payload["status_table"].to_dict(orient="records") if hasattr(unified_payload["status_table"], "to_dict") else unified_payload["status_table"],
        "macro_regime": unified_payload["regime_cards"],
        "source_status": status.to_dict(),
        "data_gaps": "Macro feeds can be delayed or require optional keys.",
    }
    if show_prompt_context:
        with st.expander("Prompt context", expanded=False):
            st.json(redact_secrets(str(context)))
    if st.button("Generate neutral AI summary", key="macro_ai"):
        response = analyze_overview_neutral(context, preferred=selected_ai)
        st.markdown(response.text)
        st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")

page_footer(st)
