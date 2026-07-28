from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.ai_analysis import analyze_stock_neutral
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
import lib.charts as charts
from lib.equity_scenarios import compute_equity_flow_proxy, compute_equity_scenario_matrix, compute_equity_technical_diagnostics
from lib.fundamentals import build_financial_overview
from lib.market_data import fetch_history
from lib.options_flow import GAMMA_CAVEAT, build_options_dashboard, get_options_expirations
from lib.terminal_ui import intelligence_card, mini_bar, severity_badge, status_badge, terminal_page_header, terminal_section_header
from lib.ui import page_footer, render_status, render_table

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    px = None
    go = None


st.set_page_config(page_title="Stock Analyzer", layout="wide")
terminal_page_header(
    st,
    "Stock Analyzer",
    "Single-name terminal overview with technical state, fundamentals, options proxy, event context, and neutral AI.",
    meta=[
        {"label": "Gamma", "value": "proxy estimate", "tone": "estimated"},
        {"label": "Financials", "value": "yfinance when available", "tone": "info"},
        {"label": "Language", "value": "neutral", "tone": "fresh"},
    ],
)

ticker = st.sidebar.text_input("Ticker", "AAPL").upper()
benchmark = st.sidebar.text_input("Benchmark", "SPY").upper()
sector_proxy = st.sidebar.text_input("Sector ETF proxy", "XLK").upper()
horizon = st.sidebar.selectbox("Horizon", ["intraday", "1w", "1m", "3m"], index=1)
provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
preferred_provider = st.sidebar.selectbox("AI provider", provider_names, index=0)
use_local = st.sidebar.checkbox("Use local Ollama if available", value=False)
show_prompt_context = st.sidebar.checkbox("Show prompt context", value=False)

selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider


def _fmt(value, digits: int = 2, suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except Exception:
        return str(value)


def _normalize_history_columns(data, ticker_symbol: str):
    normalizer = getattr(charts, "normalize_price_history_columns", None)
    if callable(normalizer):
        return normalizer(data, ticker_symbol)
    if data is None or getattr(data, "empty", True) or not isinstance(getattr(data, "columns", None), pd.MultiIndex):
        return data
    ticker_key = (ticker_symbol or "").upper()
    for level in range(data.columns.nlevels):
        match = next((value for value in data.columns.get_level_values(level) if str(value).upper() == ticker_key), None)
        if match is not None:
            return data.xs(match, axis=1, level=level, drop_level=True).copy()
    flattened = data.copy()
    flattened.columns = [" ".join(str(part) for part in column if str(part)).strip() for column in flattened.columns]
    return flattened


def _price_chart(ticker_symbol: str):
    history, status = fetch_history(ticker_symbol, period="1y")
    render_status(st, status)
    if px is None or history is None or getattr(history, "empty", True):
        render_table(st, history)
        return
    frame = _normalize_history_columns(history.copy(), ticker_symbol).reset_index()
    x_col = frame.columns[0]
    close_col = next((column for column in ["Adj Close", "Close", "adj close", "close"] if column in frame.columns), None)
    if close_col is None:
        render_table(st, frame)
        return
    fig = px.line(frame, x=x_col, y=close_col, title=f"{ticker_symbol} price", template="plotly_dark")
    fig.update_layout(margin=dict(l=12, r=12, t=44, b=28))
    st.plotly_chart(fig, use_container_width=True)


def _financial_charts(overview: dict):
    income = overview.get("income")
    margins = overview.get("margins")
    cashflow = overview.get("cashflow")
    balance = overview.get("balance")
    if px is not None and income is not None and not getattr(income, "empty", True):
        plot_income = income.reset_index().rename(columns={"index": "period"})
        y_cols = [col for col in ["revenue", "net_income", "gross_profit", "operating_income"] if col in plot_income.columns]
        if y_cols:
            fig = px.bar(plot_income, x="period", y=y_cols, barmode="group", title="Revenue / Income", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
    if px is not None and margins is not None and not getattr(margins, "empty", True):
        fig = px.line(margins.reset_index().rename(columns={"index": "period"}), x="period", y=list(margins.columns), title="Margins", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    if px is not None and cashflow is not None and not getattr(cashflow, "empty", True):
        plot_cf = cashflow.reset_index().rename(columns={"index": "period"})
        y_cols = [col for col in ["operating_cash_flow", "capex", "free_cash_flow"] if col in plot_cf.columns]
        if y_cols:
            fig = px.bar(plot_cf, x="period", y=y_cols, barmode="group", title="Cash Flow", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
    if px is not None and balance is not None and not getattr(balance, "empty", True):
        plot_bs = balance.reset_index().rename(columns={"index": "period"})
        y_cols = [col for col in ["cash_and_equivalents", "total_debt", "net_debt", "shareholders_equity"] if col in plot_bs.columns]
        if y_cols:
            fig = px.bar(plot_bs, x="period", y=y_cols, barmode="group", title="Balance Sheet", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)


diagnostics, diag_status = compute_equity_technical_diagnostics(ticker, benchmark=benchmark, sector_proxy=sector_proxy)
scenario, scenario_status = compute_equity_scenario_matrix(ticker, horizon=horizon)
flow, flow_status = compute_equity_flow_proxy(ticker)
overview, financial_status = build_financial_overview(ticker)

tabs = st.tabs(["Terminal Overview", "Price & Technicals", "Financial Overview", "Valuation & Quality", "Options / Gamma Proxy", "News & Events", "Scenario"])

with tabs[0]:
    terminal_section_header(st, "Terminal Overview", "Compact single-name command panel.")
    head_cols = st.columns([1.15, 1.15, 1.15, 1.15])
    with head_cols[0]:
        st.metric("Latest price", _fmt(diagnostics.get("latest_price")))
    with head_cols[1]:
        st.metric("RSI", _fmt(diagnostics.get("rsi")))
    with head_cols[2]:
        st.metric("Realized vol", _fmt((diagnostics.get("realized_volatility") or 0) * 100, suffix="%") if diagnostics.get("realized_volatility") is not None else "N/A")
    with head_cols[3]:
        st.metric("Range position", _fmt((diagnostics.get("range_52w_position") or 0) * 100, suffix="%") if diagnostics.get("range_52w_position") is not None else "N/A")
    grid_left, grid_right = st.columns([1.65, 1])
    with grid_left:
        _price_chart(ticker)
    with grid_right:
        intelligence_card(st, title="Technical State", summary=diagnostics.get("macd_regime", "Data gap"), severity="watch", tags=[diagnostics.get("rsi_bucket", "Data gap"), diagnostics.get("realized_volatility_regime", "Data gap")], source="equity_scenarios", freshness=diag_status.refreshed_status())
        intelligence_card(st, title="Fundamental Quality", summary=str(overview.get("balance_quality", {}).get("data_gap") or "Financial statement quality metrics available where yfinance fields exist."), severity="watch", tags=["valuation", "quality"], source="fundamentals", freshness=financial_status.refreshed_status())
        intelligence_card(st, title="Options / Gamma Mini-Panel", summary=GAMMA_CAVEAT, severity="watch", tags=["options", "proxy"], source="yfinance options", freshness="estimated")
        intelligence_card(st, title="Event Context", summary="Use News Intelligence for public feed clustering; this panel keeps ticker context neutral.", severity="watch", tags=["events", "AI"], source="public feeds optional", freshness="estimated")
    st.markdown(mini_bar(abs((diagnostics.get("price_vs_50dma") or 0) * 100), label="Distance vs 50DMA", color="#38bdf8"), unsafe_allow_html=True)
    st.markdown(mini_bar(abs((diagnostics.get("drawdown_from_52w_high") or 0) * 100), label="Drawdown from 52W high", color="#f59e0b"), unsafe_allow_html=True)

with tabs[1]:
    terminal_section_header(st, "Price & Technicals", "Trend, relative strength, volume proxy, and support/resistance context.")
    render_status(st, diag_status)
    render_table(st, pd.DataFrame([diagnostics]))
    terminal_section_header(st, "Volume / Flow Proxy", "Free data proxy; confirmed fund flows require optional providers.")
    render_status(st, flow_status)
    render_table(st, pd.DataFrame([flow]))

with tabs[2]:
    terminal_section_header(st, "Financial Overview", "Revenue, margins, cash flow, balance sheet, and data availability.")
    st.page_link("pages/15_Financial_Terminal.py", label="Open in Financial Terminal")
    render_status(st, financial_status)
    availability = pd.DataFrame([{"dataset": key, "available": value} for key, value in overview.get("availability", {}).items()])
    render_table(st, availability)
    _financial_charts(overview)

with tabs[3]:
    terminal_section_header(st, "Valuation & Quality", "Multiples and balance quality where yfinance fields are available.")
    render_status(st, financial_status)
    ratios = overview.get("ratios", {})
    quality = overview.get("balance_quality", {})
    ratio_cols = st.columns(4)
    for idx, (label, value) in enumerate(ratios.items()):
        with ratio_cols[idx % 4]:
            st.metric(label.replace("_", " ").title(), _fmt(value))
    render_table(st, pd.DataFrame([quality]))

with tabs[4]:
    terminal_section_header(st, "Options / Gamma Proxy", "Open-interest, max pain, expiry concentration, and gamma proxy caveats.")
    expirations, expiry_status = get_options_expirations(ticker)
    render_status(st, expiry_status)
    expiry = st.selectbox("Expiry", expirations, index=0) if expirations else None
    dashboard, options_status = build_options_dashboard(ticker, expiry)
    render_status(st, options_status)
    st.warning(GAMMA_CAVEAT)
    summary = {
        "put_call_oi_ratio": dashboard.get("put_call_oi_ratio"),
        "put_call_volume_ratio": dashboard.get("put_call_volume_ratio"),
        "max_pain_proxy": dashboard.get("max_pain_proxy", {}).get("max_pain_strike"),
        "underlying_price": dashboard.get("underlying_price"),
        "caveat": dashboard.get("caveat"),
    }
    metric_cols = st.columns(4)
    for idx, (label, value) in enumerate(summary.items()):
        with metric_cols[idx % 4]:
            st.metric(label.replace("_", " ").title(), _fmt(value) if label != "caveat" else str(value))
    gamma = dashboard.get("gamma_proxy")
    if px is not None and gamma is not None and not getattr(gamma, "empty", True):
        fig = px.bar(gamma, x="strike", y="gamma_proxy", color="side", title="Gamma Proxy By Strike", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    render_table(st, dashboard.get("largest_oi_strikes"))
    render_table(st, dashboard.get("expiry_concentration"))
    with st.expander("Raw gamma proxy table", expanded=False):
        render_table(st, gamma)

with tabs[5]:
    terminal_section_header(st, "News & Events", "Ticker event context and neutral AI note.")
    intelligence_card(st, title="News Mini-Feed", summary="Use the News Intelligence page for clustered public feed cards, maps, and source freshness.", severity="watch", tags=["news", "events"], freshness="estimated")
    st.caption(f"Provider: {select_ai_provider(selected_ai).provider} | Model: {select_ai_provider(selected_ai).model}")
    context = {
        "ticker": ticker,
        "diagnostics": diagnostics,
        "flow": flow,
        "financial_availability": overview.get("availability"),
        "scenario": scenario.head(10).to_dict(orient="records") if hasattr(scenario, "head") else scenario,
        "source_status": [diag_status.to_dict(), flow_status.to_dict(), scenario_status.to_dict(), financial_status.to_dict()],
        "data_gaps": "Financial statements and options may be unavailable for some tickers.",
    }
    if show_prompt_context:
        with st.expander("Prompt context", expanded=False):
            st.json(redact_secrets(str(context)))
    if st.button("Generate neutral AI summary", key="stock_ai"):
        response = analyze_stock_neutral(context, preferred=selected_ai)
        st.markdown(response.text)
        st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")

with tabs[6]:
    terminal_section_header(st, "Neutral Scenario Matrix", "Evidence-weighted scenarios, not prediction certainty.")
    render_status(st, scenario_status)
    render_table(st, scenario)

page_footer(st)
