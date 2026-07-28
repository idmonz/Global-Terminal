from __future__ import annotations

import streamlit as st

from lib.options_chain_ingestion import build_option_chain_snapshot
from lib.options_chain_iv import build_chain_iv_snapshot
from lib.options_vol_surface import build_smile_table, build_skew_table, build_term_structure_table, build_vol_surface_snapshot
from lib.options_book_risk import build_option_book_risk_snapshot
from lib.options_book_stress import build_option_book_stress_snapshot
from lib.options_lab_page_layout import DEFAULT_OPTION_INPUT, build_options_lab_page_payload
from lib.options_lab_workflow_actions import run_options_lab_action
from lib.options_strategy_templates import build_strategy_payoff, list_option_strategy_templates
from lib.quant_diagnostics_report import build_quant_diagnostics_report
from lib.research_session_state import get_research_session_state, persist_last_action_result

NOTICE = "Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions."

st.set_page_config(page_title="Options & Quant Model Lab", layout="wide")
st.title("Options Chain, Volatility Surface & Quant Diagnostics Lab")
st.caption(NOTICE)

session_state = get_research_session_state(st.session_state)
with st.sidebar:
    st.subheader("Calculator inputs")
    demo_mode = st.checkbox("Enable explicitly labeled demo panels", value=False, help="When off, option-book and quant diagnostics do not load sample data.")
    model = st.selectbox("Model", ["black_scholes", "black_76", "garman_kohlhagen"])
    option_type = st.selectbox("Option type", ["call", "put"])
    underlying = st.number_input("Underlying / futures price", value=float(DEFAULT_OPTION_INPUT["underlying_price"]), min_value=0.0001)
    strike = st.number_input("Strike", value=float(DEFAULT_OPTION_INPUT["strike"]), min_value=0.0001)
    t = st.number_input("Time to expiry (years)", value=float(DEFAULT_OPTION_INPUT["time_to_expiry_years"]), min_value=0.0001)
    rate = st.number_input("Risk-free / domestic rate", value=float(DEFAULT_OPTION_INPUT["risk_free_rate"]))
    carry = st.number_input("Dividend yield / foreign rate", value=0.0)
    vol = st.number_input("Volatility", value=float(DEFAULT_OPTION_INPUT["volatility"]), min_value=0.0001)
    premium = st.number_input("Supplied premium for IV/PnL", value=float(DEFAULT_OPTION_INPUT["premium"]), min_value=0.0001)

input_payload = {"option_type": option_type, "underlying_price": underlying, "strike": strike, "time_to_expiry_years": t, "risk_free_rate": rate, "dividend_yield": carry, "foreign_rate": carry, "domestic_rate": rate, "futures_price": underlying, "volatility": vol, "premium": premium, "model": model, "contract_multiplier": 100.0}
payload = build_options_lab_page_payload(input_payload, demo_mode=demo_mode)

tabs = st.tabs(["Calculator", "Greeks / IV", "Payoff Templates", "Option Chain CSV", "Vol Surface", "Option Book", "Quant Diagnostics", "Reports", "Raw payload"])
with tabs[0]:
    st.info(payload["notice"])
    st.metric("Theoretical premium", round(payload["pricing"]["price"], 6))
    st.json(payload["price_card"], expanded=False)
with tabs[1]:
    st.dataframe(payload["greeks_table"], use_container_width=True)
    st.json(payload["iv_solver"], expanded=False)
with tabs[2]:
    st.dataframe(payload["scenario_table"]["rows"], use_container_width=True)
    template = st.selectbox("Payoff template", [row["template"] for row in list_option_strategy_templates()])
    if st.button("Build sample payoff profile"):
        sample = build_strategy_payoff(template, {"option_type": option_type, "strike": strike, "premium": premium, "price_grid": [underlying * x for x in [0.8, 0.9, 1.0, 1.1, 1.2]], "underlying_cost": underlying, "call_strike": strike, "put_strike": strike, "lower_strike": strike * 0.95, "upper_strike": strike * 1.05, "lower_premium": premium, "upper_premium": premium / 2.0, "call_premium": premium, "put_premium": premium, "near_premium": premium, "far_premium": premium * 1.2, "near_strike": strike * 0.98, "far_strike": strike * 1.03, "center_strike": strike, "wing_width": strike * 0.05, "center_premium": premium, "premiums": {"lower_put": premium/3, "short_put": premium/2, "short_call": premium/2, "upper_call": premium/3}, "lower_put": strike*0.9, "short_put": strike*0.95, "short_call": strike*1.05, "upper_call": strike*1.1, "long_strike": strike, "short_strike": strike*1.05, "short_quantity": 2})
        st.json(sample, expanded=False)
with tabs[3]:
    st.subheader("Supplied option-chain CSV")
    st.caption("CSV upload is local/manual mode only. The app does not fetch live option chains by default.")
    csv_file = st.file_uploader("Upload option-chain CSV", type=["csv"])
    csv_text = csv_file.getvalue().decode("utf-8-sig") if csv_file else ""
    if csv_text:
        chain = build_option_chain_snapshot(csv_text)
        iv = build_chain_iv_snapshot(chain)
        st.json(chain["quality"], expanded=False)
        st.dataframe(iv["rows"], use_container_width=True)
with tabs[4]:
    st.subheader("Volatility surface snapshot")
    st.caption("Surface construction uses supplied option-chain rows only and is not a volatility forecast.")
    if csv_text:
        surface = build_vol_surface_snapshot(iv)
        st.json(surface["quality"], expanded=False)
        st.dataframe(build_smile_table(surface), use_container_width=True)
        st.dataframe(build_skew_table(surface), use_container_width=True)
        st.dataframe(build_term_structure_table(surface), use_container_width=True)
    else:
        st.warning("Upload a CSV in the Option Chain tab to build a supplied-chain surface snapshot.")
with tabs[5]:
    st.subheader("Option book risk")
    st.caption("No option-book positions are loaded unless you provide them or enable demo mode.")
    if demo_mode:
        st.info("Demo mode is enabled. The following sample is labeled demo and is not user-supplied risk.")
        sample_positions = [{"position_id":"demo_call", "underlying":"DEMO", "option_type":"call", "expiry":"2026-12-31", "strike":strike, "quantity":1, "position":"long", "premium":premium, "mark":payload["pricing"]["price"], "implied_volatility":vol, "underlying_price":underlying, "contract_multiplier":100, "source":"demo_mode"}]
        book = build_option_book_risk_snapshot(sample_positions)
        stress = build_option_book_stress_snapshot(sample_positions)
        st.json(book["totals"], expanded=False)
        st.json(stress["price_shock_grid"], expanded=False)
    else:
        st.warning("Provide local positions through workflow actions to build book risk and stress snapshots.")
with tabs[6]:
    st.subheader("Local quant diagnostics")
    st.caption("No quant series are loaded unless supplied or demo mode is explicitly enabled.")
    if demo_mode:
        st.info("Demo mode is enabled. The following series are labeled demo diagnostics.")
        demo_prices = {"DEMO": [underlying * x for x in [0.98, 1.00, 1.01, 0.99, 1.02, 1.03, 1.01]], "DEMO_2": [underlying * x for x in [0.99, 1.01, 1.00, 1.00, 1.01, 1.04, 1.02]]}
        diagnostics = build_quant_diagnostics_report(demo_prices)
        st.json(diagnostics["snapshot"], expanded=False)
    else:
        st.warning("Provide local series through workflow actions to build diagnostics.")
with tabs[7]:
    if st.button("Create options pricing report"):
        result = run_options_lab_action("OPTIONS_REPORT", {"input": input_payload})
        persist_last_action_result({"action": "OPTIONS_REPORT", "ok": result.get("ok", True), "report_id": result.get("report_id"), "research_only": True}, session_state=session_state)
        st.success(result.get("report_id", "Report payload prepared"))
    st.json(payload["provider_caveats"], expanded=False)
with tabs[8]:
    with st.expander("Raw payload"):
        st.json(payload, expanded=False)
