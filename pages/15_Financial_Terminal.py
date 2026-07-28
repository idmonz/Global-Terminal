from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.financial_charts import (
    balance_sheet_stack_chart,
    cashflow_chart,
    data_availability_heatmap,
    debt_cash_chart,
    eps_reported_estimate_chart,
    financial_waterfall_chart,
    geography_breakdown_chart,
    income_statement_stack_chart,
    margin_trend_chart,
    profitability_ratio_chart,
    revenue_breakdown_chart,
    revenue_net_income_chart,
    revenue_reported_estimate_chart,
    valuation_ratio_chart,
)
from lib.financial_terminal import build_financial_terminal_state, build_unified_financial_endpoint_payload
from lib.heatmap_layout_engine import build_heatmap_layout
from lib.terminal_ui import data_gap_badge, goal10_summary_strip, intelligence_card, metric_strip, status_badge, terminal_page_header, terminal_section_header
from lib.ui import page_footer, render_status, render_status_table, render_table


st.set_page_config(page_title="Financial Terminal", layout="wide")

with st.sidebar:
    ticker = st.text_input("Ticker", "AAPL").upper().strip()
    period = st.radio("Period", ["annual", "quarterly"], horizontal=True)
    source_mode = st.selectbox("Source mode", ["Auto", "Native only", "OpenBB preferred", "OpenBB only"], index=0)
    max_rows = st.slider("Statement rows", 4, 16, 8)

state = build_financial_terminal_state(ticker or "AAPL", period=period, source_mode=source_mode)
unified_financial = build_unified_financial_endpoint_payload(ticker or "AAPL", period=period, source_mode=source_mode)
header = state["header"]
overview = state["overview"]

terminal_page_header(
    st,
    "Financial Terminal",
    "TradingView-style reported financials, ratios, earnings context, valuation metrics, statement charts, and data availability.",
    meta=[
        {"label": "Ticker", "value": state["ticker"], "tone": "info"},
        {"label": "Company", "value": header.get("company_name"), "tone": "info"},
        {"label": "Period", "value": period, "tone": "fresh"},
        {"label": "Source", "value": state.get("source_provider", "native"), "tone": "estimated"},
        {"label": "OpenBB", "value": "installed" if state.get("openbb_installed") else "not installed", "tone": "fresh" if state.get("openbb_installed") else "watch"},
        {"label": "Fallback", "value": "used" if state.get("fallback_used") else "not used", "tone": "watch" if state.get("fallback_used") else "fresh"},
        {"label": "Forecasts", "value": "only if provider-supplied", "tone": "estimated"},
    ],
)
goal10_summary_strip(st, workspace="Financial Terminal", risk_state="watch", data_confidence="statement/provider labeled", provider_status="source mode visible", caveat="Reported statements, ratios, filings, and estimates are displayed only when provider data exists; gaps remain explicit.")

render_status(st, state["status"])

ratio_payload = overview.get("ratios", {}) if isinstance(overview, dict) else {}
metrics = [
    {"label": "Price", "value": header.get("current_price"), "delta": header.get("currency"), "freshness": state["statuses"][0].refreshed_status()},
    {"label": "Market Cap", "value": header.get("market_cap"), "delta": header.get("exchange"), "freshness": state["statuses"][0].refreshed_status()},
    {"label": "Revenue", "value": None if overview.get("income") is None else (overview["income"]["revenue"].dropna().iloc[-1] if "revenue" in overview["income"].columns and not overview["income"]["revenue"].dropna().empty else None), "delta": period, "freshness": state["statuses"][1].refreshed_status()},
    {"label": "Trailing PE", "value": ratio_payload.get("trailing_pe"), "delta": "source-derived", "freshness": state["statuses"][3].refreshed_status()},
]
metric_strip(st, metrics, columns=4)

tabs = st.tabs(
    [
        "Overview",
        "Statements",
        "Statistics",
        "Valuation",
        "Earnings",
        "Revenue",
        "Cash Flow",
        "Balance Sheet",
        "Filings / Ownership",
        "Peers",
        "Data Status",
    ]
)


def _chart(fig_payload, key: str):
    fig, frame, status = fig_payload
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, key=key)
    else:
        st.markdown(data_gap_badge("Data gap"), unsafe_allow_html=True)
        render_table(st, frame)
    render_status(st, status)


with tabs[0]:
    terminal_section_header(st, "Overview", "Reported revenue, margins, cash flow, debt/cash, key ratios, and availability.")
    left, right = st.columns([1.5, 1])
    with left:
        _chart(revenue_net_income_chart(overview.get("income")), "financial_overview_revenue_net_income")
        _chart(margin_trend_chart(overview.get("margins")), "financial_overview_margin_trend")
    with right:
        intelligence_card(
            st,
            title="Financial Coverage",
            summary="Fields are displayed only when reported by yfinance or derivable from reported statements.",
            severity="watch",
            tags=["reported", period],
            bullets=state["caveats"][:4],
            source="financial_terminal",
            freshness=state["status"].refreshed_status(),
        )
        render_table(st, pd.DataFrame([{"metric": key, "value": value} for key, value in ratio_payload.items() if value is not None]).head(12))
    c1, c2 = st.columns(2)
    with c1:
        _chart(cashflow_chart(overview.get("cashflow")), "financial_overview_cashflow")
    with c2:
        _chart(debt_cash_chart(overview.get("balance")), "financial_overview_debt_cash")
    _chart(data_availability_heatmap(state["availability"]), "financial_overview_availability")
    availability_rows = []
    if hasattr(state.get("availability"), "to_dict"):
        for row in state["availability"].to_dict(orient="records"):
            availability_rows.append(
                {
                    "symbol": row.get("field") or row.get("statement") or row.get("metric") or "financial field",
                    "group": row.get("statement") or row.get("category") or "Financial availability",
                    "quality_score": 100 if row.get("available") else 20,
                    "source": state.get("source_provider", "financial terminal"),
                    "freshness": state["status"].refreshed_status(),
                    "truth_label": "reported" if row.get("available") else "missing",
                    "tile_type": "financial",
                }
            )
    render_table(st, build_heatmap_layout(availability_rows, title="Financial Data Availability Heatmap", size_mode="equal", color_mode="data_quality", group_mode="sector")["table"])

with tabs[1]:
    terminal_section_header(st, "Statements", "Income statement, balance sheet, cash flow, and raw tables.")
    _chart(income_statement_stack_chart(state["statements"].get("income")), "financial_statements_income_stack")
    _chart(balance_sheet_stack_chart(state["statements"].get("balance")), "financial_statements_balance_stack")
    _chart(cashflow_chart(state["statements"].get("cashflow")), "financial_statements_cashflow")
    with st.expander("Income statement table", expanded=False):
        render_table(st, state["statements"].get("income").tail(max_rows) if hasattr(state["statements"].get("income"), "tail") else state["statements"].get("income"))
    with st.expander("Balance sheet table", expanded=False):
        render_table(st, state["statements"].get("balance").tail(max_rows) if hasattr(state["statements"].get("balance"), "tail") else state["statements"].get("balance"))
    with st.expander("Cash flow table", expanded=False):
        render_table(st, state["statements"].get("cashflow").tail(max_rows) if hasattr(state["statements"].get("cashflow"), "tail") else state["statements"].get("cashflow"))

with tabs[2]:
    terminal_section_header(st, "Statistics", "Valuation, profitability, liquidity, leverage, and data availability.")
    _chart(profitability_ratio_chart(ratio_payload), "financial_statistics_profitability")
    render_table(st, state["statistics"])
    missing_stats = state["statistics"][~state["statistics"]["available"]] if hasattr(state["statistics"], "columns") and "available" in state["statistics"].columns else pd.DataFrame()
    if not missing_stats.empty:
        st.warning("Some statistics are unavailable from the current provider payload.")
        render_table(st, missing_stats)

with tabs[3]:
    terminal_section_header(st, "Valuation", "Multiples and market-cap context. No fair value or directional directive is generated.")
    _chart(valuation_ratio_chart(ratio_payload), "financial_valuation_ratios")
    valuation = state["valuation"]
    valuation_rows = pd.DataFrame([{"metric": key, "value": value} for key, value in valuation.items() if key != "caveat"])
    render_table(st, valuation_rows)
    st.caption(valuation.get("caveat"))

with tabs[4]:
    terminal_section_header(st, "Earnings", "Reported vs estimate charts render only when provider-supplied estimate fields exist.")
    earnings = state["earnings"]
    st.metric("Next report date", earnings.get("next_report_date") or "Data gap")
    _chart(eps_reported_estimate_chart(earnings.get("earnings_history")), "financial_earnings_eps_reported_estimate")
    _chart(revenue_reported_estimate_chart(earnings.get("earnings_history")), "financial_earnings_revenue_reported_estimate")
    render_table(st, earnings.get("earnings_history"))

with tabs[5]:
    terminal_section_header(st, "Revenue", "Total revenue, growth, and segment/geography only when real provider data exists.")
    revenue = state["revenue"]
    _chart(revenue_net_income_chart(overview.get("income")), "financial_revenue_total_revenue")
    render_table(st, revenue.get("revenue_growth"))
    _chart(revenue_breakdown_chart(state["revenue"].get("segment_revenue")), "financial_segment_revenue_breakdown")
    _chart(geography_breakdown_chart(state["revenue"].get("geographic_revenue")), "financial_geography_revenue_breakdown")
    _chart(financial_waterfall_chart(overview.get("income")), "financial_segment_waterfall")
    st.warning(revenue.get("data_gap"))

with tabs[6]:
    terminal_section_header(st, "Cash Flow", "Operating cash flow, capex, free cash flow, and FCF margin where derivable.")
    cashflow = state["cashflow"]
    _chart(cashflow_chart(cashflow.get("cashflow")), "financial_cashflow_chart")
    render_table(st, cashflow.get("fcf_margin"))

with tabs[7]:
    terminal_section_header(st, "Balance Sheet", "Cash, debt, assets, liabilities, equity, liquidity, and leverage fields.")
    balance = state["balance_sheet"]
    _chart(balance_sheet_stack_chart(balance.get("balance")), "financial_balance_sheet_stack")
    _chart(debt_cash_chart(balance.get("balance")), "financial_balance_sheet_debt_cash")
    c1, c2 = st.columns(2)
    with c1:
        render_table(st, balance.get("liquidity_fields"))
    with c2:
        render_table(st, balance.get("leverage_fields"))

with tabs[8]:
    terminal_section_header(st, "Filings / Ownership", "Provider-supplied filing and ownership rows. Empty tables mean data gap.")
    filings = state.get("filings", pd.DataFrame())
    ownership = state.get("ownership", pd.DataFrame())
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Filings")
        render_table(st, filings)
    with c2:
        st.subheader("Ownership")
        render_table(st, ownership)

with tabs[9]:
    terminal_section_header(st, "Peers", "Provider-supplied peer comparison universe when available.")
    render_table(st, state.get("peers", pd.DataFrame()))

with tabs[10]:
    terminal_section_header(st, "Data Status", "Provider, field, availability, freshness, source, and caveat.")
    st.caption(unified_financial["caveat"])
    render_table(st, unified_financial["status_table"])
    render_status_table(st, state["statuses"])
    render_table(st, state["availability"])
    st.markdown("".join([status_badge("Forecast region", "provider data only", tone="estimated"), data_gap_badge("No fabricated estimates")]), unsafe_allow_html=True)

page_footer(st)
