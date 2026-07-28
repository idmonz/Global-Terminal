from __future__ import annotations

import streamlit as st
import pandas as pd

from lib.ai_analysis import analyze_screener_results_neutral, build_openbb_screener_ai_context
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
from lib.heatmap_layout_engine import build_heatmap_layout
from lib.screeners import (
    apply_screener_filters,
    build_bond_rates_screener,
    build_commodity_screener,
    build_cross_asset_screener,
    build_crypto_screener,
    build_etf_screener,
    build_screener_visual_summary,
    build_screener_with_source_mode,
    build_stock_screener,
    build_unified_screener_backend,
)
from lib.openbb_screener_backend import build_screener_factor_presets
from lib.terminal_ui import goal10_summary_strip, intelligence_card, mini_bar, provider_health_strip, screener_terminal_payload, terminal_page_header, terminal_section_header
from lib.ui import page_footer, render_status, render_table

try:
    import plotly.express as px
except Exception:  # pragma: no cover
    px = None


st.set_page_config(page_title="Screener", layout="wide")
terminal_page_header(
    st,
    "Screener",
    "Visual cross-asset screeners with rank badges, heatmaps, scatter diagnostics, source status, and neutral AI summaries.",
    meta=[
        {"label": "Mode", "value": "public/delayed data", "tone": "fresh"},
        {"label": "Ranks", "value": "heuristic", "tone": "estimated"},
        {"label": "Watchlist", "value": "session local", "tone": "info"},
    ],
)
provider_health_strip(st)
goal10_summary_strip(st, workspace="Screener", risk_state="watch", data_confidence="rank/source labeled", provider_status="public/delayed data", caveat="Ranks are heuristic research context. Source status, proxy labels, and missing data remain visible.")

ASSET_BUILDERS = {
    "Stocks": build_stock_screener,
    "ETFs": build_etf_screener,
    "Crypto": build_crypto_screener,
    "Bonds / Rates": build_bond_rates_screener,
    "Commodities": build_commodity_screener,
    "Cross-asset": build_cross_asset_screener,
}

with st.sidebar:
    asset_class = st.selectbox("Asset class", list(ASSET_BUILDERS), index=0)
    period = st.selectbox("Period", ["3mo", "6mo", "1y", "2y"], index=2)
    source_mode = st.selectbox("Source mode", ["Auto", "Native only", "OpenBB preferred", "OpenBB only"], index=0)
    presets = build_screener_factor_presets()
    factor_preset = st.selectbox("Factor preset", [item["preset"] for item in presets], index=0)
    min_return = st.number_input("Min 1M return %", value=-100.0, step=1.0)
    max_vol = st.number_input("Max volatility %", value=999.0, step=5.0)
    provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
    preferred_provider = st.selectbox("AI provider", provider_names, index=0)
    use_local = st.checkbox("Use local Ollama if available", value=False)
    show_prompt_context = st.checkbox("Show prompt context", value=False)

selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider
frame, status, source_status = build_unified_screener_backend(asset_class, period=period, source_mode=source_mode)
filtered = apply_screener_filters(
    frame,
    min_return_1m=None if min_return <= -100 else min_return,
    max_volatility=None if max_vol >= 999 else max_vol,
)


def _ranked(data):
    if data is None or getattr(data, "empty", True):
        return data
    output = data.copy()
    if "return_1m_pct" in output.columns:
        momentum = output["return_1m_pct"].fillna(0)
    elif "return_period_pct" in output.columns:
        momentum = output["return_period_pct"].fillna(0)
    else:
        momentum = pd.Series(0, index=output.index)
    if "realized_volatility_pct" in output.columns:
        volatility = output["realized_volatility_pct"].fillna(0)
    elif "volatility_pct" in output.columns:
        volatility = output["volatility_pct"].fillna(0)
    else:
        volatility = pd.Series(0, index=output.index)
    output["visual_rank_score"] = (momentum.rank(pct=True) * 65 + (100 - volatility.rank(pct=True) * 100) * 0.35).round(1)
    output["rank_badge"] = output["visual_rank_score"].apply(lambda value: "Constructive backdrop" if value >= 70 else "Mixed evidence" if value >= 35 else "Deteriorating breadth")
    if "data_status" not in output.columns:
        output["data_status"] = status.refreshed_status() if status is not None else "unknown"
    return output


visual_summary = build_screener_visual_summary(filtered)
ranked = visual_summary.get("heatmap_frame")

terminal_section_header(st, "Screener Snapshot", f"{asset_class} | {period} | {source_mode} | {len(ranked) if hasattr(ranked, '__len__') else 0} rows")
snapshot_cols = st.columns(4)
if ranked is not None and not getattr(ranked, "empty", True):
    with snapshot_cols[0]:
        st.metric("Rows", len(ranked))
    with snapshot_cols[1]:
        return_col = "return_1m_pct" if "return_1m_pct" in ranked.columns else "return_period_pct" if "return_period_pct" in ranked.columns else None
        st.metric("Median 1M return", f"{ranked[return_col].median():,.2f}%" if return_col else "N/A")
    with snapshot_cols[2]:
        vol_col = "realized_volatility_pct" if "realized_volatility_pct" in ranked.columns else "volatility_pct" if "volatility_pct" in ranked.columns else None
        st.metric("Median vol", f"{ranked[vol_col].median():,.2f}%" if vol_col else "N/A")
    with snapshot_cols[3]:
        st.metric("Data status", status.refreshed_status() if status is not None else "unknown")
    st.caption(f"Preset: {factor_preset} | OpenBB: {'installed' if source_status.get('openbb_installed') else 'not installed'} | Fallback allowed: {source_status.get('fallback_allowed')} | Factor coverage avg: {source_status.get('factor_coverage_avg', 0):.1f}%")
    top_row = ranked.sort_values("visual_rank_score", ascending=False).iloc[0].to_dict()
    intelligence_card(
        st,
        title=f"Top Visual Rank: {top_row.get('ticker', top_row.get('name', 'N/A'))}",
        summary=str(top_row.get("rank_badge", "Mixed evidence")),
        severity="watch",
        tags=[asset_class, "heuristic rank"],
        source=top_row.get("data_status", "screener"),
        freshness=status.refreshed_status() if status is not None else "unknown",
    )
    st.markdown(mini_bar(top_row.get("visual_rank_score", 0), label="Visual rank score", color="#38bdf8"), unsafe_allow_html=True)

tabs = st.tabs(["Table", "Heatmap", "Scatter", "AI"])

with tabs[0]:
    terminal_section_header(st, "Result Cards And Table", "Cards summarize rank context; full rows remain available below.")
    render_status(st, status)
    render_table(st, pd.DataFrame([source_status]))
    payload = screener_terminal_payload(ranked)
    st.caption(payload["caveat"])
    if "screener_watchlist" not in st.session_state:
        st.session_state["screener_watchlist"] = []
    if ranked is not None and not getattr(ranked, "empty", True):
        card_cols = st.columns(4)
        for idx, row in enumerate(ranked.sort_values("visual_rank_score", ascending=False).head(8).to_dict(orient="records")):
            with card_cols[idx % 4]:
                intelligence_card(
                    st,
                    title=str(row.get("ticker", row.get("name", "Item"))),
                    summary=str(row.get("rank_badge", "Mixed evidence")),
                    severity="watch",
                    tags=[str(row.get("asset_class", asset_class)), str(row.get("momentum_bucket", ""))],
                    source=str(row.get("data_status", "screener")),
                    freshness=status.refreshed_status() if status is not None else "unknown",
                )
        choices = ranked["ticker"].dropna().astype(str).tolist() if "ticker" in ranked.columns else []
        selected_watch = st.multiselect("Session watchlist", choices, default=[item for item in st.session_state["screener_watchlist"] if item in choices])
        st.session_state["screener_watchlist"] = selected_watch
    visible_columns = st.multiselect("Columns", list(ranked.columns) if hasattr(ranked, "columns") else [], default=list(ranked.columns[:8]) if hasattr(ranked, "columns") else [])
    render_table(st, ranked[visible_columns] if visible_columns and hasattr(ranked, "columns") else ranked)
    if payload["selected_row_detail"]:
        with st.expander("Selected row detail", expanded=False):
            st.json(payload["selected_row_detail"])
    if hasattr(ranked, "to_csv"):
        st.download_button("Export CSV", ranked.to_csv(index=False).encode("utf-8"), file_name=f"{asset_class.lower().replace(' ', '_')}_screener.csv", mime="text/csv")
    link_cols = st.columns(3)
    link_cols[0].page_link("pages/2_Stock_Analyzer.py", label="Stock Analyzer")
    link_cols[1].page_link("pages/15_Financial_Terminal.py", label="Financial Terminal")
    link_cols[2].page_link("pages/16_Portfolio_Quant_Lab.py", label="Portfolio Quant Lab")

with tabs[1]:
    terminal_section_header(st, "Heatmap", "Return-colored treemap with delayed/public source context.")
    if px is not None and ranked is not None and not getattr(ranked, "empty", True):
        color = "return_1m_pct" if "return_1m_pct" in ranked.columns else "return_period_pct"
        label = "name" if "name" in ranked.columns else "ticker"
        fig = px.treemap(ranked, path=[label], values="price" if "price" in ranked.columns else None, color=color if color in ranked.columns else None, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        render_table(st, ranked)
    if ranked is not None and not getattr(ranked, "empty", True):
        terminal_section_header(st, "Goal 10B Internal Heatmap Payload", "Shared heatmap metadata, freshness, and drilldown commands.")
        heatmap_rows = ranked.to_dict(orient="records")
        render_table(st, build_heatmap_layout(heatmap_rows, title=f"{asset_class} Screener Heatmap", size_mode="equal", color_mode="daily_change", group_mode="asset_class")["table"])

with tabs[2]:
    terminal_section_header(st, "Scatter", "Return versus volatility, sized by visual rank where available.")
    if px is not None and ranked is not None and not getattr(ranked, "empty", True):
        x_col = "return_1m_pct" if "return_1m_pct" in ranked.columns else "return_period_pct"
        y_col = "realized_volatility_pct" if "realized_volatility_pct" in ranked.columns else "volatility_pct"
        if x_col in ranked.columns and y_col in ranked.columns:
            fig = px.scatter(ranked, x=x_col, y=y_col, size="visual_rank_score", color="rank_badge", hover_name="ticker", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            render_table(st, ranked)
    else:
        render_table(st, ranked)

with tabs[3]:
    st.caption(f"Provider: {select_ai_provider(selected_ai).provider} | Model: {select_ai_provider(selected_ai).model}")
    context = build_openbb_screener_ai_context(
        {
            "asset_class": asset_class,
            "filters": {"min_return_1m": min_return, "max_volatility": max_vol},
            "rows": ranked.head(30) if hasattr(ranked, "head") else pd.DataFrame(),
            "source_status": source_status,
            "data_gaps": "Fundamental, options, crypto derivatives, and AUM fields depend on optional providers.",
        }
    )
    if show_prompt_context:
        with st.expander("Prompt context", expanded=False):
            st.json(redact_secrets(str(context)))
    if st.button("Generate neutral AI summary", key="screener_ai"):
        response = analyze_screener_results_neutral(context, preferred=selected_ai)
        st.markdown(response.text)
        st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")

page_footer(st)
