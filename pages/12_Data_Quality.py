from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.data_status import error_result, ok_result
from lib.energy_data import get_eia_api_key_status
from lib.ai_providers import list_available_ai_providers
from lib.provider_diagnostics import provider_health_summary
from lib.provider_quality import build_provider_quality_scorecard, build_provider_quality_summary
from lib.openbb_bridge import openbb_available_result
from lib.terminal_ui import goal10_summary_strip, metric_strip, terminal_page_header, terminal_section_header
from lib.ui import page_footer, render_status_table
from lib.worldmonitor_adapter import check_worldmonitor_status


st.set_page_config(page_title="Data Quality", layout="wide")
terminal_page_header(
    st,
    "Data Quality Command Ledger",
    "Source freshness, provider quality, explicit data gaps, and optional-backend readiness.",
    meta=[
        {"label": "Policy", "value": "No fabricated data", "tone": "fresh"},
        {"label": "Providers", "value": "optional keys visible", "tone": "estimated"},
        {"label": "Mode", "value": "research", "tone": "info"},
    ],
)
goal10_summary_strip(st, workspace="Data Quality", risk_state="data gap", data_confidence="audited", provider_status="diagnostics visible", caveat="This page highlights stale, missing-key, proxy, estimated, and optional-backend states before raw status rows.")
st.info("For provider capability matrices, optional-key diagnostics, AIS/flight caveats, and setup guidance, open the Data Provider Center page.")
st.caption(provider_health_summary()["caveat"])

statuses = [
    ok_result(source="equity breadth module", provider="Equity breadth", is_estimated=True, coverage="module available"),
    ok_result(source="yfinance equity data", provider="yfinance equity", coverage="optional live feed"),
    ok_result(source="yfinance options", provider="yfinance options", is_estimated=True, coverage="optional delayed feed"),
    get_eia_api_key_status(),
    ok_result(source="yfinance energy fallback", provider="Energy fallback", coverage="optional live feed"),
    ok_result(source="GDELT/RSS", provider="Geopolitical news", coverage="public feeds; rate limits possible"),
    check_worldmonitor_status(),
    ok_result(source="risk lab price data", provider="Risk Lab", coverage="module available"),
    ok_result(source="scenario engine", provider="Scenario engine", is_estimated=True, coverage="module available"),
    ok_result(source="AI provider layer", provider="AI analysis", is_estimated=True, coverage=", ".join(provider.provider for provider in list_available_ai_providers() if provider.available)),
    ok_result(source="fundamentals visualization", provider="Financial Overview", coverage="yfinance optional feed"),
    ok_result(source="options gamma proxy", provider="Options Flow", is_estimated=True, coverage="delayed option chain proxy"),
    ok_result(source="screeners", provider="Screener", is_estimated=True, coverage="stocks, ETFs, crypto, bonds, commodities, cross-asset"),
    openbb_available_result(),
    ok_result(source="map visualization", provider="Map Viz", is_estimated=True, coverage="static/proxy maps; AIS unavailable without provider"),
]

terminal_section_header(st, "Quality Summary", "Compact scorecard built from the current page-level status ledger.")
quality = build_provider_quality_scorecard([status.to_dict() for status in statuses])
quality_summary = build_provider_quality_summary(quality)
metric_strip(
    st,
    [
        {"label": "Average Quality", "value": quality_summary["average_quality"], "delta": quality_summary["summary_label"], "freshness": "estimated"},
        {"label": "Ready", "value": quality_summary["ready_count"], "delta": "sources", "freshness": "fresh"},
        {"label": "Limited", "value": quality_summary["limited_count"], "delta": "review", "freshness": "estimated"},
        {"label": "Gap", "value": quality_summary["gap_count"], "delta": "visible", "freshness": "missing" if quality_summary["gap_count"] else "fresh"},
    ],
)

tabs = st.tabs(["Status Ledger", "Provider Quality"])
with tabs[0]:
    terminal_section_header(st, "Status Ledger", "Provider/source status rows with freshness and coverage.")
    render_status_table(st, statuses)

with tabs[1]:
    terminal_section_header(st, "Provider Quality", "Readiness scoring derived from status rows, not synthetic feed success.")
    st.dataframe(quality, use_container_width=True, hide_index=True)
    if quality_summary["top_gaps"]:
        st.warning("Top visible gaps")
        st.dataframe(pd.DataFrame(quality_summary["top_gaps"]), use_container_width=True, hide_index=True)

page_footer(st)
