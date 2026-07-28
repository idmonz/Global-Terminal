from __future__ import annotations

import streamlit as st

from lib.ai_analysis import summarize_cross_asset_scenarios_neutral
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
from lib.scenario_engine import build_cross_asset_scenario, build_macro_energy_scenario_evidence
from lib.ui import page_footer, render_status, render_table


st.set_page_config(page_title="Scenario Lab", layout="wide")
st.title("Scenario Lab")

asset_type = st.sidebar.selectbox("Asset mode", ["Equity", "Crypto", "Energy", "Portfolio"])
default_asset = {"Equity": "SPY", "Crypto": "BTCUSDT", "Energy": "CL=F", "Portfolio": "SPY, TLT, CL=F, BTC-USD"}[asset_type]
asset = st.sidebar.text_input("Asset or basket", default_asset)
horizon = st.sidebar.selectbox("Horizon", ["intraday", "1w", "1m", "3m"], index=1)
modules = st.sidebar.multiselect("Evidence modules", ["technical", "breadth", "flow", "derivatives", "on-chain", "macro", "news", "geopolitical", "risk"], default=["technical", "risk"])
source_mode = st.sidebar.selectbox("Unified source mode", ["auto", "native_only", "openbb_preferred", "openbb_only"], index=0)
provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
preferred_provider = st.sidebar.selectbox("AI provider", provider_names, index=0)
use_local = st.sidebar.checkbox("Use local Ollama if available", value=False)
show_prompt_context = st.sidebar.checkbox("Show prompt context", value=False)
selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider

scenario, status = build_cross_asset_scenario(asset_type.lower(), asset, horizon=horizon, modules=modules)
render_status(st, status)
render_table(st, scenario)

if any(module in modules for module in ["macro", "geopolitical", "risk"]) or asset_type == "Energy":
    st.subheader("Macro / Energy / Chokepoint Evidence")
    evidence_payload = build_macro_energy_scenario_evidence(source_mode=source_mode)
    st.caption(evidence_payload["caveat"])
    st.json(evidence_payload["macro_regime"])
    render_table(st, evidence_payload["energy_risk"]["energy_market_impact"])
    render_table(st, evidence_payload["chokepoint_risk"]["cards"])
else:
    evidence_payload = {"caveat": "Macro/energy evidence not selected.", "macro_regime": {}, "energy_risk": {}, "chokepoint_risk": {}}

st.subheader("AI Scenario Summary")
st.caption(f"Provider: {select_ai_provider(selected_ai).provider} | Model: {select_ai_provider(selected_ai).model}")
context = {
    "asset_type": asset_type,
    "asset": asset,
    "horizon": horizon,
    "modules": modules,
    "scenario": scenario.head(20).to_dict(orient="records") if hasattr(scenario, "head") else scenario,
    "macro_energy_evidence": evidence_payload,
    "source_status": status.to_dict(),
}
if show_prompt_context:
    with st.expander("Prompt context", expanded=False):
        st.json(redact_secrets(str(context)))
if st.button("Generate neutral AI summary", key="scenario_ai"):
    response = summarize_cross_asset_scenarios_neutral(context, preferred=selected_ai)
    st.markdown(response.text)
    st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")

page_footer(st)
