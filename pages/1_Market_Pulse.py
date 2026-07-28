from __future__ import annotations

import streamlit as st

from lib.ai_analysis import analyze_overview_neutral
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
from lib.market_data import latest_price_snapshot
from lib.ui import page_footer, render_status, render_table


st.set_page_config(page_title="Market Pulse", layout="wide")
st.title("Market Pulse")

tickers = st.text_input("Ticker set", "SPY, QQQ, IWM, GLD, CL=F, BTC-USD")
provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
preferred_provider = st.sidebar.selectbox("AI provider", provider_names, index=0)
use_local = st.sidebar.checkbox("Use local Ollama if available", value=False)
show_prompt_context = st.sidebar.checkbox("Show prompt context", value=False)
selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider
symbols = [item.strip().upper() for item in tickers.split(",") if item.strip()]
data, status = latest_price_snapshot(symbols)
render_status(st, status)
render_table(st, data)

st.subheader("AI Market Pulse")
st.caption(f"Provider: {select_ai_provider(selected_ai).provider} | Model: {select_ai_provider(selected_ai).model}")
context = {
    "symbols": symbols,
    "snapshot": data.head(20).to_dict(orient="records") if hasattr(data, "head") else data,
    "source_status": status.to_dict(),
}
if show_prompt_context:
    with st.expander("Prompt context", expanded=False):
        st.json(redact_secrets(str(context)))
if st.button("Generate neutral AI summary", key="market_pulse_ai"):
    response = analyze_overview_neutral(context, preferred=selected_ai)
    st.markdown(response.text)
    st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")

page_footer(st)
