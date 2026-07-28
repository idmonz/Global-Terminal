from __future__ import annotations

import streamlit as st

from lib.charts import make_treemap
from lib.heatmap_layout_engine import build_heatmap_layout
from lib.heatmaps import (
    build_cross_asset_heatmap,
    build_crypto_heatmap,
    build_g7_heatmap,
    build_korea_heatmap,
    build_nasdaq100_heatmap,
    build_sector_heatmap,
    build_sp500_heatmap,
)
from lib.ui import page_footer, render_chart_or_table, render_status, render_table, unique_existing_columns


st.set_page_config(page_title="Global Heatmaps", layout="wide")
st.title("Global Heatmaps")

metric_options = {"Daily %": "daily_return", "Weekly %": "weekly_return", "Monthly %": "monthly_return", "YTD %": "ytd_return"}
controls = st.columns([1, 1, 3])
selected_metric = controls[0].selectbox("Color metric", list(metric_options.keys()), index=0)
metric_col = metric_options[selected_metric]
size_mode = controls[1].radio("Size mode", ["Market cap / proxy", "Equal weight"], index=0, horizontal=True)
controls[2].caption(f"Heatmap color: {selected_metric}. Size: {size_mode}. Estimates and missing values are labeled in the table.")


def show_heatmap(label: str, builder, *, parent_col: str, title: str) -> None:
    data, status = builder()
    render_status(st, status)
    if getattr(data, "empty", True):
        st.info(f"{label} data unavailable.")
        return
    frame = data.copy()
    value_col = "size_value"
    if size_mode == "Equal weight":
        frame["_equal_weight"] = 1
        value_col = "_equal_weight"
    fig = make_treemap(
        frame,
        title=title,
        label_col="name",
        parent_col=parent_col,
        value_col=value_col,
        color_col=metric_col,
        color_label=selected_metric,
        source=status.source,
        fetched_at=status.fetched_at.isoformat(),
    )
    render_chart_or_table(st, fig, frame)
    table_cols = unique_existing_columns(frame, ["ticker", "name", "company", parent_col, "price", metric_col, "daily_return", "weekly_return", "monthly_return", "ytd_return", "regime", "data_quality"])
    render_table(st, frame[table_cols])
    with st.expander("Goal 10B heatmap metadata", expanded=False):
        color_mode = {
            "daily_return": "daily_change",
            "weekly_return": "weekly_change",
            "monthly_return": "monthly_change",
        }.get(metric_col, "daily_change")
        render_table(st, build_heatmap_layout(frame, title=title, size_mode="market_cap" if size_mode != "Equal weight" else "equal", color_mode=color_mode, group_mode=parent_col)["table"])


tabs = st.tabs(["US S&P 500", "US Sectors", "Nasdaq 100", "Korea KOSPI/KOSDAQ", "G7 Markets", "Crypto Market", "Cross-Asset"])
with tabs[0]:
    show_heatmap("S&P 500", build_sp500_heatmap, parent_col="sector", title=f"S&P 500 Heatmap - {selected_metric}")
with tabs[1]:
    show_heatmap("US sectors", build_sector_heatmap, parent_col="sector", title=f"US Sector ETF Heatmap - {selected_metric}")
with tabs[2]:
    show_heatmap("Nasdaq 100", build_nasdaq100_heatmap, parent_col="sector", title=f"Nasdaq 100 Heatmap - {selected_metric}")
with tabs[3]:
    show_heatmap("Korea", build_korea_heatmap, parent_col="sector", title=f"Korea Watchlist - {selected_metric}")
with tabs[4]:
    show_heatmap("G7 markets", build_g7_heatmap, parent_col="group", title=f"G7 + Korea Markets - {selected_metric}")
with tabs[5]:
    show_heatmap("Crypto", build_crypto_heatmap, parent_col="group", title=f"Crypto Market Proxy - {selected_metric}")
with tabs[6]:
    show_heatmap("Cross-asset", build_cross_asset_heatmap, parent_col="group", title=f"Cross-Asset Heatmap - {selected_metric}")

page_footer(st)
