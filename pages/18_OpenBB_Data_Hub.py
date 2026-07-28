from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.openbb_bridge import OPENBB_CAVEAT, openbb_available_result
from lib.openbb_catalog import (
    build_openbb_capability_catalog,
    list_openbb_domains,
    list_openbb_required_keys,
    openbb_app_mapping_table,
    openbb_endpoint_status_table,
)
from lib.openbb_diagnostics import (
    build_openbb_diagnostics_table,
    build_openbb_runtime_diagnostics_payload,
    build_openbb_setup_guide_payload,
    openbb_capability_health_check,
    openbb_installation_status,
    run_openbb_button_probe_report,
    test_openbb_sample_equity_query,
    test_openbb_sample_etf_query,
    test_openbb_sample_macro_query,
    test_openbb_sample_options_query,
)
from lib.provider_quality import build_openbb_probe_quality_table, build_provider_quality_summary
from lib.provider_probe_runner import run_provider_probes
from lib.provider_probe_visuals import build_provider_probe_metric_cards, build_provider_probe_table
from lib.openbb_ai_context_router import build_mcp_ready_openbb_endpoint_manifest
from lib.openbb_provider_adapter import (
    get_openbb_balance_sheet,
    get_openbb_cash_flow,
    get_openbb_commodity_spot,
    get_openbb_company_profile,
    get_openbb_equity_active,
    get_openbb_equity_gainers,
    get_openbb_equity_losers,
    get_openbb_equity_screener,
    get_openbb_estimates,
    get_openbb_etf_active,
    get_openbb_etf_country_exposure,
    get_openbb_etf_gainers,
    get_openbb_etf_holdings,
    get_openbb_etf_info,
    get_openbb_etf_losers,
    get_openbb_etf_sector_exposure,
    get_openbb_filings,
    get_openbb_income_statement,
    get_openbb_metrics,
    get_openbb_options_chain,
    get_openbb_options_surface,
    get_openbb_petroleum_status_report,
    get_openbb_price_history,
    get_openbb_ratios,
    get_openbb_treasury_rates,
    get_openbb_unusual_options,
    get_openbb_yield_curve,
)
from lib.terminal_ui import goal10_summary_strip, metric_strip, terminal_page_header, terminal_section_header
from lib.ui import page_footer, render_status, render_table


st.set_page_config(page_title="OpenBB Data Hub", layout="wide")

status = openbb_installation_status()
availability = openbb_available_result()

terminal_page_header(
    st,
    "OpenBB Data Hub",
    "Optional OpenBB backend bridge, capability catalog, provider-key status, and button-triggered diagnostics.",
    meta=[
        {"label": "Backend", "value": "Optional", "tone": "info"},
        {"label": "Installed", "value": "Yes" if status["installed"] else "No", "tone": "fresh" if status["installed"] else "watch"},
        {"label": "Fallback", "value": "Native providers remain active", "tone": "fresh"},
    ],
)
st.caption(OPENBB_CAVEAT)
goal10_summary_strip(st, workspace="OpenBB Data Hub", risk_state="watch", data_confidence="runtime/catalog labeled", provider_status="OpenBB optional", caveat=OPENBB_CAVEAT)

tabs = st.tabs(
    [
        "Overview",
        "Installation Status",
        "Capability Catalog",
        "Provider Keys",
        "Financial Data",
        "ETF Data",
        "Options / Derivatives",
        "Macro / Rates",
        "Commodity / Energy",
        "Screener Backend",
        "Diagnostics",
        "Runtime Provider Probes",
        "License / Caveats",
    ]
)


def _render_result(result):
    render_status(st, result)
    if hasattr(result.data, "empty"):
        render_table(st, result.data)
    elif result.data is not None:
        st.json(result.data)


with tabs[0]:
    terminal_section_header(st, "Overview", "Optional backend state and application mapping")
    metric_strip(
        st,
        [
            {"label": "Installed", "value": "Yes" if status["installed"] else "No", "delta": status.get("version") or "optional", "freshness": "fresh" if status["installed"] else "missing"},
            {"label": "Base Launch", "value": "Works without OpenBB", "delta": "native fallback", "freshness": "fresh"},
            {"label": "License", "value": "User must verify", "delta": "provider rights", "freshness": "estimated"},
            {"label": "Keys", "value": "Optional", "delta": "never displayed", "freshness": "estimated"},
        ],
    )
    render_status(st, availability)
    render_table(st, openbb_app_mapping_table())
    st.json(build_openbb_setup_guide_payload())

with tabs[1]:
    terminal_section_header(st, "Installation Status", "Local package status and optional backend mode")
    render_table(st, pd.DataFrame([status]))
    render_table(st, build_openbb_diagnostics_table())

with tabs[2]:
    terminal_section_header(st, "Capability Catalog", "OpenBB target domains mapped to local app areas")
    catalog = build_openbb_capability_catalog()
    domain = st.selectbox("Domain", ["All"] + list_openbb_domains())
    area = st.text_input("Filter app area", "")
    filtered = catalog
    if domain != "All":
        filtered = filtered[filtered["openbb_domain"] == domain]
    if area:
        filtered = filtered[filtered["app_area"].str.contains(area, case=False, na=False)]
    render_table(st, filtered)

with tabs[3]:
    terminal_section_header(st, "Provider Keys", "Environment variable status without exposing values")
    render_table(st, list_openbb_required_keys())
    st.info("Configured means the environment variable exists. Secret values are never printed.")

with tabs[4]:
    terminal_section_header(st, "Financial Data", "Button-triggered OpenBB probes for stock financial datasets")
    ticker = st.text_input("Ticker", "AAPL", key="openbb_fin_ticker").upper().strip()
    period = st.radio("Period", ["annual", "quarterly"], horizontal=True, key="openbb_fin_period")
    probes = {
        "Profile": lambda: get_openbb_company_profile(ticker),
        "Price History": lambda: get_openbb_price_history(ticker),
        "Income": lambda: get_openbb_income_statement(ticker, period=period),
        "Balance": lambda: get_openbb_balance_sheet(ticker, period=period),
        "Cash Flow": lambda: get_openbb_cash_flow(ticker, period=period),
        "Ratios": lambda: get_openbb_ratios(ticker, period=period),
        "Metrics": lambda: get_openbb_metrics(ticker, period=period),
        "Estimates": lambda: get_openbb_estimates(ticker),
        "Filings": lambda: get_openbb_filings(ticker),
    }
    selected = st.selectbox("Dataset", list(probes), key="openbb_fin_dataset")
    if st.button("Run financial probe", key="openbb_fin_probe"):
        _render_result(probes[selected]())

with tabs[5]:
    terminal_section_header(st, "ETF Data", "Button-triggered OpenBB probes for ETF metadata and exposure")
    symbol = st.text_input("ETF", "SPY", key="openbb_etf_symbol").upper().strip()
    probes = {
        "Info": lambda: get_openbb_etf_info(symbol),
        "Holdings": lambda: get_openbb_etf_holdings(symbol),
        "Sector Exposure": lambda: get_openbb_etf_sector_exposure(symbol),
        "Country Exposure": lambda: get_openbb_etf_country_exposure(symbol),
        "ETF Gainers": get_openbb_etf_gainers,
        "ETF Losers": get_openbb_etf_losers,
        "ETF Active": get_openbb_etf_active,
    }
    selected = st.selectbox("ETF dataset", list(probes), key="openbb_etf_dataset")
    if st.button("Run ETF probe", key="openbb_etf_probe"):
        _render_result(probes[selected]())

with tabs[6]:
    terminal_section_header(st, "Options / Derivatives", "Optional provider probes; paid data rights may be required")
    ticker = st.text_input("Options ticker", "SPY", key="openbb_options_ticker").upper().strip()
    probes = {
        "Options Chain": lambda: get_openbb_options_chain(ticker),
        "Options Surface": lambda: get_openbb_options_surface(ticker),
        "Unusual Options": lambda: get_openbb_unusual_options(ticker),
    }
    selected = st.selectbox("Options dataset", list(probes), key="openbb_options_dataset")
    if st.button("Run options probe", key="openbb_options_probe"):
        _render_result(probes[selected]())

with tabs[7]:
    terminal_section_header(st, "Macro / Rates", "Treasury and macro probes")
    probes = {"Treasury Rates": get_openbb_treasury_rates, "Yield Curve": get_openbb_yield_curve}
    selected = st.selectbox("Macro/rates dataset", list(probes), key="openbb_macro_dataset")
    if st.button("Run macro/rates probe", key="openbb_macro_probe"):
        _render_result(probes[selected]())

with tabs[8]:
    terminal_section_header(st, "Commodity / Energy", "Energy and commodity probes")
    commodity = st.text_input("Commodity symbol/category", "WTI", key="openbb_commodity_symbol")
    probes = {
        "Commodity Spot": lambda: get_openbb_commodity_spot(commodity),
        "Petroleum Status Report": get_openbb_petroleum_status_report,
    }
    selected = st.selectbox("Commodity dataset", list(probes), key="openbb_commodity_dataset")
    if st.button("Run commodity probe", key="openbb_commodity_probe"):
        _render_result(probes[selected]())

with tabs[9]:
    terminal_section_header(st, "Screener Backend", "OpenBB screener and market mover probes")
    probes = {
        "Equity Screener": get_openbb_equity_screener,
        "Equity Gainers": get_openbb_equity_gainers,
        "Equity Losers": get_openbb_equity_losers,
        "Equity Active": get_openbb_equity_active,
    }
    selected = st.selectbox("Screener dataset", list(probes), key="openbb_screener_dataset")
    if st.button("Run screener probe", key="openbb_screener_probe"):
        _render_result(probes[selected]())

with tabs[10]:
    terminal_section_header(st, "Diagnostics", "Safe status tables and sample probes")
    render_table(st, openbb_capability_health_check())
    render_table(st, openbb_endpoint_status_table())
    runtime_payload = build_openbb_runtime_diagnostics_payload()
    st.caption(runtime_payload["probe_policy"])
    terminal_section_header(st, "Runtime Capability Matrix", "Cataloged endpoints compared with local OpenBB runtime")
    render_table(st, runtime_payload["runtime_matrix"])
    terminal_section_header(st, "Endpoint Gaps", "OpenBB-compatible endpoints not exposed by the current runtime")
    render_table(st, runtime_payload["endpoint_gaps"])
    terminal_section_header(st, "Provider Key Gaps", "Optional provider keys without displaying values")
    render_table(st, runtime_payload["provider_key_gaps"])
    cols = st.columns(4)
    if cols[0].button("Sample equity"):
        st.json(test_openbb_sample_equity_query())
    if cols[1].button("Sample macro"):
        st.json(test_openbb_sample_macro_query())
    if cols[2].button("Sample ETF"):
        st.json(test_openbb_sample_etf_query())
    if cols[3].button("Sample options"):
        st.json(test_openbb_sample_options_query())
    if st.button("Run optional real probe report", key="openbb_real_probe_report"):
        report = run_openbb_button_probe_report()
        render_table(st, report)
        probe_quality = build_openbb_probe_quality_table(report)
        probe_summary = build_provider_quality_summary(probe_quality)
        metric_strip(
            st,
            [
                {"label": "Probe Quality", "value": probe_summary["average_quality"], "delta": probe_summary["summary_label"], "freshness": "estimated"},
                {"label": "Ready", "value": probe_summary["ready_count"], "delta": "checks", "freshness": "fresh"},
                {"label": "Limited", "value": probe_summary["limited_count"], "delta": "checks", "freshness": "estimated"},
                {"label": "Gap", "value": probe_summary["gap_count"], "delta": "checks", "freshness": "missing" if probe_summary["gap_count"] else "fresh"},
            ],
        )
        render_table(st, probe_quality)
    terminal_section_header(st, "AI Context Preparation Manifest", "Endpoint schemas for future optional integration; no server surface is started here.")
    render_table(st, pd.DataFrame(build_mcp_ready_openbb_endpoint_manifest()).head(50))

with tabs[11]:
    terminal_section_header(st, "Runtime Provider Probes", "Goal 10 provider diagnostics beside the optional OpenBB bridge")
    probe_results = run_provider_probes(dry_run=True)
    metric_strip(st, build_provider_probe_metric_cards(probe_results), columns=4)
    render_table(st, build_provider_probe_table(probe_results))
    st.info("Provider probes are lightweight diagnostics. Missing API keys, rate limits, and provider outages may affect availability.")

with tabs[12]:
    terminal_section_header(st, "License / Caveats", "Boundary policy for optional OpenBB usage")
    st.warning(OPENBB_CAVEAT)
    caveats = pd.DataFrame(
        [
            {"policy": "Optional dependency", "detail": "Base launch must work without OpenBB installed."},
            {"policy": "No source vendoring", "detail": "OpenBB source archives and external trees are excluded from release packages."},
            {"policy": "No paid data claim", "detail": "OpenBB/provider APIs may require keys, paid plans, or separate rights."},
            {"policy": "Fallback behavior", "detail": "Native yfinance, FRED, EIA, Binance, CoinGecko, DefiLlama, and local modules remain active."},
            {"policy": "AI context", "detail": "Only compact, source-labeled summaries should be sent to AI analysis."},
        ]
    )
    render_table(st, caveats)

page_footer(st)
