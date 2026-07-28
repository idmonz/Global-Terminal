from __future__ import annotations

import streamlit as st

from lib.portfolio import holdings_frame, parse_weights
from lib.stress_tests import build_stress_test_matrix
from lib.ui import page_footer, render_status, render_table


st.set_page_config(page_title="Portfolio", layout="wide")
st.title("Portfolio")
st.info("For editable portfolios, backtests, strategy candidates, optimizers, forecasts, and attribution, open the Portfolio Quant Lab page.")

tickers_text = st.text_input("Portfolio tickers", "SPY, TLT, CL=F, BTC-USD")
weights_text = st.text_input("Weights", "")
tickers = [item.strip().upper() for item in tickers_text.split(",") if item.strip()]
weights = parse_weights(tickers, weights_text)
render_table(st, holdings_frame(tickers, weights))

stress, status = build_stress_test_matrix(tickers, weights)
render_status(st, status)
render_table(st, stress[["scenario", "estimated_portfolio_impact", "caveat"]])

page_footer(st)
