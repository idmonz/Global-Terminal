from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.ai_analysis import analyze_etf_neutral
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
from lib.equity_scenarios import compute_equity_scenario_matrix, compute_equity_technical_diagnostics
from lib.ui import page_footer, render_status, render_table


st.set_page_config(page_title="ETF Analyzer", layout="wide")
st.title("ETF Analyzer")

ticker = st.sidebar.text_input("ETF ticker", "SPY").upper()
provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
preferred_provider = st.sidebar.selectbox("AI provider", provider_names, index=0)
use_local = st.sidebar.checkbox("Use local Ollama if available", value=False)
show_prompt_context = st.sidebar.checkbox("Show prompt context", value=False)
selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider

tabs = st.tabs(["Price & Technicals", "Scenario", "AI"])

diagnostics, status = compute_equity_technical_diagnostics(ticker, benchmark="SPY")
scenarios, scenario_status = compute_equity_scenario_matrix(ticker, horizon="1m")

with tabs[0]:
    render_status(st, status)
    render_table(st, pd.DataFrame([diagnostics]))

with tabs[1]:
    render_status(st, scenario_status)
    render_table(st, scenarios)

with tabs[2]:
    st.caption(f"Provider: {select_ai_provider(selected_ai).provider} | Model: {select_ai_provider(selected_ai).model}")
    context = {
        "ticker": ticker,
        "diagnostics": diagnostics,
        "scenario": scenarios.head(20).to_dict(orient="records") if hasattr(scenarios, "head") else scenarios,
        "source_status": [status.to_dict(), scenario_status.to_dict()],
    }
    if show_prompt_context:
        with st.expander("Prompt context", expanded=False):
            st.json(redact_secrets(str(context)))
    if st.button("Generate neutral AI summary", key="etf_ai"):
        response = analyze_etf_neutral(context, preferred=selected_ai)
        st.markdown(response.text)
        st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")

page_footer(st)
