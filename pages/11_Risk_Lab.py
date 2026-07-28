from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.market_data import fetch_many_price_histories, fetch_price_history
from lib.portfolio import parse_weights
from lib.risk import (
    build_risk_summary,
    compute_beta,
    compute_correlation_matrix,
    compute_drawdown_series,
    compute_historical_cvar,
    compute_historical_var,
    compute_portfolio_return_series,
    compute_realized_volatility,
    compute_risk_contribution_proxy,
    compute_rolling_sharpe,
)
from lib.stress_tests import build_stress_test_matrix
from lib.ui import page_footer, render_status, render_table


st.set_page_config(page_title="Risk Lab", layout="wide")
st.title("Risk Lab")

tickers_text = st.sidebar.text_input("Tickers", "SPY, TLT, CL=F, BTC-USD")
weights_text = st.sidebar.text_input("Weights", "")
benchmark = st.sidebar.text_input("Benchmark", "SPY").upper()
period = st.sidebar.selectbox("Lookback period", ["6mo", "1y", "2y"], index=1)
confidence = st.sidebar.slider("Confidence level", 0.90, 0.99, 0.95, 0.01)
rolling_window = st.sidebar.slider("Rolling window", 20, 126, 63)

tickers = [item.strip().upper() for item in tickers_text.split(",") if item.strip()]
weights = parse_weights(tickers, weights_text)
histories, price_status = fetch_many_price_histories(tickers, period=period)
returns = pd.DataFrame({ticker: frame.set_index("date")["close"].pct_change() for ticker, frame in histories.items() if not frame.empty}).dropna(how="all")
portfolio_returns = compute_portfolio_return_series(returns, weights[: len(returns.columns)] if not returns.empty else weights)
benchmark_history, benchmark_status = fetch_price_history(benchmark, period=period)
benchmark_returns = benchmark_history.set_index("date")["close"].pct_change() if not benchmark_history.empty else None
summary, summary_status = build_risk_summary(returns, benchmark_returns, weights[: len(returns.columns)] if not returns.empty else weights)

tabs = st.tabs(["Portfolio Risk Overview", "Return & Drawdown", "Volatility & Sharpe", "VaR / CVaR", "Correlation & Beta", "Stress Tests", "Risk Contribution", "Data Status"])
with tabs[0]:
    render_status(st, summary_status)
    render_table(st, pd.DataFrame([summary]))
with tabs[1]:
    render_table(st, pd.DataFrame({"portfolio_return": portfolio_returns, "drawdown": compute_drawdown_series(portfolio_returns)}).reset_index())
with tabs[2]:
    rolling = compute_rolling_sharpe(portfolio_returns, window=rolling_window)
    render_table(st, pd.DataFrame({"rolling_sharpe": rolling}).reset_index())
    st.metric("Realized volatility", f"{compute_realized_volatility(portfolio_returns):.2%}" if not portfolio_returns.empty else "n/a")
with tabs[3]:
    st.metric("Historical VaR", f"{compute_historical_var(portfolio_returns, confidence):.2%}" if not portfolio_returns.empty else "n/a")
    st.metric("Historical CVaR", f"{compute_historical_cvar(portfolio_returns, confidence):.2%}" if not portfolio_returns.empty else "n/a")
with tabs[4]:
    render_table(st, compute_correlation_matrix(returns).reset_index())
    if benchmark_returns is not None and not portfolio_returns.empty:
        st.metric("Beta vs benchmark", f"{compute_beta(portfolio_returns, benchmark_returns):.2f}")
with tabs[5]:
    stress, stress_status = build_stress_test_matrix(tickers, weights)
    render_status(st, stress_status)
    render_table(st, stress[["scenario", "estimated_portfolio_impact", "caveat", "data_gaps"]])
with tabs[6]:
    render_table(st, compute_risk_contribution_proxy(returns, weights[: len(returns.columns)] if not returns.empty else None))
with tabs[7]:
    render_status(st, price_status)
    render_status(st, benchmark_status)
    render_status(st, summary_status)

page_footer(st)

