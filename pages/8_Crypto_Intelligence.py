from __future__ import annotations

import streamlit as st

from lib.ai_analysis import analyze_crypto_neutral
from lib.ai_providers import list_available_ai_providers, select_ai_provider
from lib.ai_safety import redact_secrets
import lib.crypto_derivatives as crypto_derivatives
from lib.crypto_onchain import build_onchain_dashboard
from lib.crypto_prices import get_coingecko_markets, get_crypto_market_overview
from lib.crypto_scenarios import crypto_scenario_matrix, estimate_liquidation_pressure_map
from lib.data_status import DataResult, provider_status_table
from lib.heatmap_layout_engine import build_heatmap_layout
from lib.market_radar import build_crypto_derivatives_radar
import lib.map_viz as map_viz
from lib.source_freshness import source_freshness_table
from lib.terminal_ui import crypto_terminal_payload, goal10_summary_strip, intelligence_card, mini_bar, provider_health_strip, terminal_page_header, terminal_section_header
from lib.ui import page_footer, render_status, render_table

try:
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except Exception:  # pragma: no cover
    pd = None
    px = None
    go = None
    make_subplots = None


st.set_page_config(page_title="Crypto Intelligence", layout="wide")
terminal_page_header(
    st,
    "Crypto Intelligence",
    "Derivatives radar, OI/price structure, funding, positioning, estimated liquidation pressure, on-chain context, and neutral scenarios.",
    meta=[
        {"label": "Mode", "value": "free/public where available", "tone": "fresh"},
        {"label": "Liquidations", "value": "estimated pressure proxy", "tone": "estimated"},
        {"label": "Live stream", "value": "not claimed", "tone": "info"},
    ],
)
provider_health_strip(st)
goal10_summary_strip(st, workspace="Crypto Derivatives Desk", risk_state="watch", data_confidence="public/proxy", provider_status="public feeds ready", caveat="Funding, OI, and liquidation pressure panels remain source-labeled; official heatmaps require a real provider.")

DEFAULT_SYMBOLS = getattr(crypto_derivatives, "DEFAULT_SYMBOLS", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"])


def _normalize_symbol(symbol: str) -> str:
    normalizer = getattr(crypto_derivatives, "normalize_symbol", None)
    if callable(normalizer):
        return normalizer(symbol)
    cleaned = "".join(ch for ch in (symbol or "").upper() if ch.isalnum())
    return f"{cleaned}T" if cleaned.endswith("USD") and not cleaned.endswith("USDT") else cleaned


def _source_freshness_chart(statuses=None):
    builder = getattr(map_viz, "build_source_freshness_chart", None)
    if callable(builder):
        return builder(statuses)
    return None, statuses, DataResult(ok=False, source="source freshness chart", provider="map_viz", error="source freshness chart helper unavailable in current Streamlit process.", freshness_status="error")


def _optional_provider_status(provider: str) -> DataResult:
    builder = getattr(crypto_derivatives, "optional_provider_status", None)
    if callable(builder):
        return builder(provider)
    return DataResult(
        ok=False,
        source=provider,
        provider=provider,
        error="Unavailable: optional paid provider/API key required.",
        coverage="optional paid provider",
        is_paid_required=True,
        freshness_status="error",
    )


def _fmt(value, digits: int = 2, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except Exception:
        return str(value)


def _metric(label: str, value, digits: int = 2, suffix: str = "") -> None:
    st.metric(label, _fmt(value, digits=digits, suffix=suffix))


def _status_caption(status: DataResult | None) -> str:
    if status is None:
        return ""
    return f"{status.source} | {status.refreshed_status()} | {status.fetched_at.isoformat()}"


def _line_chart(frame, *, x: str, y: str, title: str, key: str, status: DataResult | None = None):
    if px is None or frame is None or getattr(frame, "empty", True) or y not in frame.columns:
        render_table(st, frame)
        return
    fig = px.line(frame, x=x if x in frame.columns else None, y=y, title=title, template="plotly_dark")
    fig.update_layout(margin=dict(l=12, r=12, t=48, b=36))
    if status is not None:
        fig.add_annotation(text=_status_caption(status), x=0, y=-0.18, xref="paper", yref="paper", showarrow=False, font=dict(size=11), align="left")
    st.plotly_chart(fig, use_container_width=True, key=key)


def _price_volume_chart(klines, status: DataResult | None, *, key: str):
    if go is None or make_subplots is None or klines is None or getattr(klines, "empty", True):
        render_table(st, klines)
        return
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.04)
    fig.add_trace(go.Candlestick(x=klines["open_time"], open=klines["open"], high=klines["high"], low=klines["low"], close=klines["close"], name="Price"), row=1, col=1)
    fig.add_trace(go.Bar(x=klines["open_time"], y=klines["volume"], name="Volume", marker_color="#64748b"), row=2, col=1)
    fig.update_layout(template="plotly_dark", title="Futures Price And Volume", margin=dict(l=12, r=12, t=48, b=36), xaxis_rangeslider_visible=False)
    if status is not None:
        fig.add_annotation(text=_status_caption(status), x=0, y=-0.18, xref="paper", yref="paper", showarrow=False, font=dict(size=11), align="left")
    st.plotly_chart(fig, use_container_width=True, key=key)


def _pressure_chart(frame, status: DataResult | None, *, key: str):
    if px is None or frame is None or getattr(frame, "empty", True):
        render_table(st, frame)
        return
    fig = px.bar(
        frame.sort_values("level"),
        x="level",
        y="pressure_score",
        color="side",
        hover_data=["leverage_band", "distance_pct", "confidence", "caveat"],
        title="Estimated Liquidation Pressure Map",
        template="plotly_dark",
    )
    fig.update_layout(margin=dict(l=12, r=12, t=48, b=36), yaxis_title="Estimated pressure score")
    if status is not None:
        fig.add_annotation(text=_status_caption(status), x=0, y=-0.18, xref="paper", yref="paper", showarrow=False, font=dict(size=11), align="left")
    st.plotly_chart(fig, use_container_width=True, key=key)


def _radar_chart(frame, *, key: str):
    if px is None or frame is None or getattr(frame, "empty", True):
        render_table(st, frame)
        return
    fig = px.bar(frame, x="score", y="component", color="label", orientation="h", title="Derivatives Radar", template="plotly_dark")
    fig.update_layout(margin=dict(l=12, r=12, t=48, b=32), xaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True, key=key)


def _crypto_heatmap_rows(markets, snapshot: dict, pressure_rows=None):
    rows = []
    if markets is not None and hasattr(markets, "head"):
        for row in markets.head(30).to_dict(orient="records"):
            rows.append(
                {
                    "symbol": str(row.get("symbol", "")).upper(),
                    "name": row.get("name") or row.get("symbol"),
                    "category": "Crypto",
                    "market_cap": row.get("market_cap") or 1,
                    "tvl": row.get("total_volume") or row.get("market_cap") or 1,
                    "daily_return": row.get("price_change_percentage_24h") or row.get("price_change_24h") or 0,
                    "source": "CoinGecko public",
                    "freshness": "estimated",
                    "tile_type": "crypto",
                }
            )
    symbol_row = {
        "symbol": snapshot.get("symbol") or symbol,
        "name": snapshot.get("symbol") or symbol,
        "category": "Derivatives",
        "market_cap": 1,
        "funding_rate": (snapshot.get("funding_rate") or 0) * 100,
        "open_interest": snapshot.get("open_interest") or 1,
        "open_interest_change": snapshot.get("open_interest_change") or 0,
        "liquidation_pressure": 0,
        "source": "Binance public endpoints where available",
        "freshness": snapshot_status.refreshed_status() if snapshot_status is not None else "estimated",
        "truth_label": "proxy",
        "tile_type": "crypto",
    }
    if pressure_rows is not None and hasattr(pressure_rows, "empty") and not pressure_rows.empty and "pressure_score" in pressure_rows.columns:
        symbol_row["liquidation_pressure"] = float(pressure_rows["pressure_score"].max())
    rows.append(symbol_row)
    return rows


def _oi_price_dual_chart(klines, oi_history, status: DataResult | None, *, key: str):
    if go is None or make_subplots is None or klines is None or oi_history is None or getattr(klines, "empty", True) or getattr(oi_history, "empty", True):
        render_table(st, oi_history)
        return
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=klines["open_time"], y=klines["close"], name="Price", line=dict(color="#38bdf8")), secondary_y=False)
    y_col = "sum_open_interest_value" if "sum_open_interest_value" in oi_history.columns else "sum_open_interest"
    fig.add_trace(go.Scatter(x=oi_history["timestamp"], y=oi_history[y_col], name="Open interest", line=dict(color="#f59e0b")), secondary_y=True)
    fig.update_layout(template="plotly_dark", title="OI vs Price", margin=dict(l=12, r=12, t=48, b=36))
    fig.update_yaxes(title_text="Price", secondary_y=False)
    fig.update_yaxes(title_text="Open interest", secondary_y=True)
    if status is not None:
        fig.add_annotation(text=_status_caption(status), x=0, y=-0.18, xref="paper", yref="paper", showarrow=False, font=dict(size=11), align="left")
    st.plotly_chart(fig, use_container_width=True, key=key)


with st.sidebar:
    selected = st.selectbox("Symbol", DEFAULT_SYMBOLS, index=0)
    custom = st.text_input("Custom Binance USD-M symbol", value="")
    symbol = _normalize_symbol(custom or selected)
    interval = st.selectbox("Price interval", ["5m", "15m", "1h", "4h", "1d"], index=2)
    period = st.selectbox("Derivatives period", ["5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"], index=3)
    limit = st.slider("Lookback limit", 24, 300, 120, 12)
    show_pressure = st.toggle("Show estimated liquidation pressure map", value=True)
    show_onchain = st.toggle("Show DefiLlama on-chain data", value=True)
    show_scenarios = st.toggle("Show scenario matrix", value=True)
    show_raw_status = st.toggle("Show raw data status", value=True)
    provider_names = ["auto"] + [provider.provider for provider in list_available_ai_providers()]
    preferred_provider = st.selectbox("AI provider", provider_names, index=0)
    use_local = st.checkbox("Use local Ollama if available", value=False)
    show_prompt_context = st.checkbox("Show prompt context", value=False)
    st.button("Refresh")
selected_ai = "ollama" if use_local and select_ai_provider("ollama").available else preferred_provider

statuses: list[DataResult] = []

try:
    timeseries, ts_status = crypto_derivatives.build_derivatives_timeseries(symbol, period=period, limit=limit)
except Exception as exc:
    timeseries, ts_status = {}, DataResult(ok=False, source="Binance derivatives time series", provider="Binance USD-M Futures", error=str(exc), freshness_status="error")
statuses.append(ts_status)

try:
    snapshot, snapshot_status = crypto_derivatives.build_derivatives_snapshot(symbol, period=period)
except Exception as exc:
    snapshot, snapshot_status = {"symbol": symbol, "data_gaps": str(exc)}, DataResult(ok=False, source="Binance derivatives snapshot", provider="Binance USD-M Futures", error=str(exc), freshness_status="error")
statuses.append(snapshot_status)

try:
    market_overview, market_status = get_crypto_market_overview()
except Exception as exc:
    market_overview, market_status = {}, DataResult(ok=False, source="CoinGecko market overview", provider="CoinGecko", error=str(exc), freshness_status="error")
statuses.append(market_status)

try:
    coingecko_markets, coingecko_status = get_coingecko_markets(limit=50)
except Exception as exc:
    coingecko_markets, coingecko_status = None, DataResult(ok=False, source="CoinGecko coins markets", provider="CoinGecko", error=str(exc), freshness_status="error")
statuses.append(coingecko_status)

onchain = {}
onchain_status = None
if show_onchain:
    try:
        onchain, onchain_status = build_onchain_dashboard()
    except Exception as exc:
        onchain_status = DataResult(ok=False, source="DefiLlama on-chain dashboard", provider="DefiLlama", error=str(exc), freshness_status="error")
    statuses.append(onchain_status)

klines = timeseries.get("klines") if isinstance(timeseries, dict) else None
oi_history = timeseries.get("open_interest") if isinstance(timeseries, dict) else None
funding = timeseries.get("funding") if isinstance(timeseries, dict) else None
taker = timeseries.get("taker") if isinstance(timeseries, dict) else None
global_ratio = timeseries.get("global_long_short") if isinstance(timeseries, dict) else None
top_account = timeseries.get("top_trader_account") if isinstance(timeseries, dict) else None
top_position = timeseries.get("top_trader_position") if isinstance(timeseries, dict) else None

pressure_map = None
pressure_status = None
if show_pressure:
    pressure_map, pressure_status = estimate_liquidation_pressure_map(klines=klines, oi_history=oi_history, snapshot=snapshot)
    statuses.append(pressure_status)

scenario_rows = None
if show_scenarios:
    scenario_rows = crypto_scenario_matrix(symbol=symbol, klines=klines, oi_history=oi_history, snapshot=snapshot, pressure_map=pressure_map)

derivatives_radar = build_crypto_derivatives_radar(snapshot, pressure_map)

tabs = st.tabs([
    "Overview",
    "Futures & Perps",
    "Open Interest",
    "Funding & Basis",
    "Taker Flow",
    "Long/Short Bias",
    "Liquidations",
    "On-chain & Stablecoins",
    "Scenario Monitor",
    "Data Status",
])

with tabs[0]:
    terminal_section_header(st, "Terminal Overview", "Crowding, leverage, liquidity pressure, and source state.")
    crypto_payload = crypto_terminal_payload(snapshot)
    st.caption(crypto_payload["caveat"])
    render_status(st, snapshot_status)
    render_status(st, market_status)
    overview_cols = st.columns([1.15, 1])
    with overview_cols[0]:
        _radar_chart(derivatives_radar, key="crypto_derivatives_radar")
    with overview_cols[1]:
        radar_row = derivatives_radar.iloc[0].to_dict() if hasattr(derivatives_radar, "iloc") and not derivatives_radar.empty else {}
        intelligence_card(
            st,
            title="Derivatives Stress Proxy",
            summary=radar_row.get("label", "Data gap"),
            severity="medium" if radar_row.get("score", 0) >= 55 else "watch",
            tags=["heuristic", "public derivatives"],
            source=radar_row.get("method", "market_radar"),
            freshness="estimated",
        )
        st.markdown(mini_bar(radar_row.get("score", 0), label="Radar score", color="#f59e0b"), unsafe_allow_html=True)
        intelligence_card(
            st,
            title="Source Caveat",
            summary="Funding, OI, taker flow, and long/short ratios are context signals. Estimated liquidation pressure is not official exchange liquidation data.",
            severity="watch",
            tags=["data caveat", "proxy"],
            source="Binance public endpoints where available",
            freshness=snapshot_status.refreshed_status(),
        )
    cols = st.columns(4)
    with cols[0]:
        _metric("Mark price", snapshot.get("mark_price"))
    with cols[1]:
        _metric("Open interest", snapshot.get("open_interest"), digits=0)
    with cols[2]:
        _metric("Funding rate", (snapshot.get("funding_rate") or 0) * 100 if snapshot.get("funding_rate") is not None else None, digits=4, suffix="%")
    with cols[3]:
        _metric("Premium / basis", snapshot.get("premium_pct"), digits=4, suffix="%")
    cols = st.columns(4)
    with cols[0]:
        _metric("Taker buy/sell ratio", snapshot.get("taker_buy_sell_ratio"))
    with cols[1]:
        _metric("Global long/short ratio", snapshot.get("global_long_short_ratio"))
    with cols[2]:
        _metric("Top trader position ratio", snapshot.get("top_trader_position_ratio"))
    with cols[3]:
        _metric("Top-100 market cap", market_overview.get("total_market_cap"), digits=0)
    _price_volume_chart(klines, ts_status, key="crypto_overview_price_volume")
    terminal_section_header(st, "Crypto Heatmap Modes", "Project-native heatmaps for price, funding, OI, liquidation pressure proxy, and TVL/volume context.")
    heatmap_rows = _crypto_heatmap_rows(coingecko_markets, snapshot, pressure_map)
    heatmap_mode_tabs = st.tabs(["Price", "Funding", "OI Change", "Liquidation Proxy", "TVL/Volume"])
    heatmap_specs = [
        ("Crypto Price Change", "market_cap", "daily_change"),
        ("Funding Heatmap", "open_interest", "funding_rate"),
        ("Open Interest Change", "open_interest", "open_interest_change"),
        ("Liquidation Pressure Proxy", "open_interest", "liquidation_pressure"),
        ("TVL / Volume Context", "tvl", "daily_change"),
    ]
    for heatmap_tab, (title, size_mode, color_mode) in zip(heatmap_mode_tabs, heatmap_specs):
        with heatmap_tab:
            render_table(st, build_heatmap_layout(heatmap_rows, title=title, size_mode=size_mode, color_mode=color_mode, group_mode="crypto_sector")["table"])
    if coingecko_markets is not None:
        render_table(st, coingecko_markets.head(25) if hasattr(coingecko_markets, "head") else coingecko_markets)

with tabs[1]:
    st.subheader("Futures And Perps")
    _line_chart(oi_history, x="timestamp", y="sum_open_interest_value", title="Open Interest Value", key="crypto_futures_oi_value", status=ts_status)
    _line_chart(funding, x="funding_time", y="funding_rate", title="Funding Rate", key="crypto_futures_funding_rate", status=ts_status)
    _line_chart(taker, x="timestamp", y="buy_sell_ratio", title="Taker Buy/Sell Ratio", key="crypto_futures_taker_ratio", status=ts_status)
    _line_chart(global_ratio, x="timestamp", y="long_short_ratio", title="Global Long/Short Ratio", key="crypto_futures_global_ls_ratio", status=ts_status)

with tabs[2]:
    st.subheader("Open Interest")
    _metric("Current OI", snapshot.get("open_interest"), digits=0)
    _oi_price_dual_chart(klines, oi_history, ts_status, key="crypto_oi_price_dual")
    if pd is not None and oi_history is not None and not getattr(oi_history, "empty", True):
        oi = oi_history.copy()
        if len(oi) > 1 and oi["sum_open_interest"].iloc[0]:
            oi["oi_change_pct"] = (oi["sum_open_interest"] / oi["sum_open_interest"].iloc[0] - 1.0) * 100.0
            _line_chart(oi, x="timestamp", y="oi_change_pct", title="Open Interest Change %", key="crypto_oi_change_pct", status=ts_status)
        _line_chart(oi, x="timestamp", y="sum_open_interest", title="Open Interest Contracts", key="crypto_oi_contracts", status=ts_status)
    st.caption("Interpretation context: price and OI combinations can indicate participation, short-covering, liquidation, or consolidation evidence. This is not personalized financial advice.")

with tabs[3]:
    st.subheader("Funding And Basis")
    _metric("Current funding", (snapshot.get("funding_rate") or 0) * 100 if snapshot.get("funding_rate") is not None else None, digits=4, suffix="%")
    _metric("Premium / basis", snapshot.get("premium_pct"), digits=4, suffix="%")
    _line_chart(funding, x="funding_time", y="funding_rate", title="Funding History", key="crypto_funding_history", status=ts_status)
    if px is not None and funding is not None and not getattr(funding, "empty", True) and "funding_rate" in funding.columns:
        fig = px.histogram(funding, x="funding_rate", nbins=30, title="Funding Distribution", template="plotly_dark")
        fig.update_layout(margin=dict(l=12, r=12, t=48, b=36))
        st.plotly_chart(fig, use_container_width=True, key="crypto_funding_distribution")
    st.caption("Positive or negative funding is treated as crowding context, not direction advice.")

with tabs[4]:
    st.subheader("Taker Flow")
    _line_chart(taker, x="timestamp", y="buy_sell_ratio", title="Taker Buy/Sell Ratio", key="crypto_taker_flow_ratio", status=ts_status)
    if pd is not None and taker is not None and not getattr(taker, "empty", True):
        flow = taker.copy()
        flow["rolling_imbalance"] = flow["buy_sell_ratio"].rolling(5, min_periods=1).mean()
        _line_chart(flow, x="timestamp", y="rolling_imbalance", title="Rolling Taker Imbalance", key="crypto_taker_flow_rolling_imbalance", status=ts_status)
        render_table(st, flow.tail(25))

with tabs[5]:
    st.subheader("Long/Short Bias")
    cols = st.columns(3)
    with cols[0]:
        _metric("Global long/short", snapshot.get("global_long_short_ratio"))
    with cols[1]:
        _metric("Top account long/short", snapshot.get("top_trader_account_ratio"))
    with cols[2]:
        _metric("Top position long/short", snapshot.get("top_trader_position_ratio"))
    _line_chart(global_ratio, x="timestamp", y="long_short_ratio", title="Global Account Long/Short Ratio", key="crypto_ls_global_account", status=ts_status)
    _line_chart(top_account, x="timestamp", y="long_short_ratio", title="Top Trader Account Ratio", key="crypto_ls_top_account", status=ts_status)
    _line_chart(top_position, x="timestamp", y="long_short_ratio", title="Top Trader Position Ratio", key="crypto_ls_top_position", status=ts_status)

with tabs[6]:
    st.subheader("Liquidations")
    st.warning("Websocket live liquidation stream deferred. Binance forceOrder streams are not implemented in this Streamlit MVP.")
    if show_pressure:
        st.caption("Estimated liquidation pressure map. This is not official exchange liquidation data.")
        _pressure_chart(pressure_map, pressure_status, key="crypto_liquidation_pressure_map")
        render_table(st, pressure_map.head(50) if hasattr(pressure_map, "head") else pressure_map)
    else:
        st.info("Estimated liquidation pressure map is disabled in the sidebar.")

with tabs[7]:
    st.subheader("On-chain And Stablecoins")
    if not show_onchain:
        st.info("DefiLlama on-chain data is disabled in the sidebar.")
    else:
        render_status(st, onchain_status)
        card_cols = st.columns(3)
        for idx, key in enumerate(["chains", "protocols", "stablecoins"]):
            data = onchain.get(key)
            count = len(data) if hasattr(data, "__len__") else 0
            with card_cols[idx]:
                intelligence_card(
                    st,
                    title=key.replace("_", " ").title(),
                    summary=f"{count} public rows available from DefiLlama where reachable.",
                    severity="watch",
                    tags=["on-chain", "public"],
                    source="DefiLlama",
                    freshness=onchain_status.refreshed_status() if onchain_status else "unknown",
                )
        chain_cols = ["name", "chain", "tvl", "change_1d", "change_7d"]
        for key, label in [
            ("chains", "Chain TVL"),
            ("protocols", "Top Protocol TVL"),
            ("stablecoins", "Stablecoins"),
            ("stablecoins_by_chain", "Stablecoins By Chain"),
            ("dex_volume", "DEX Volume"),
            ("fees", "Fees"),
        ]:
            st.markdown(f"#### {label}")
            data = onchain.get(key)
            if data is not None and hasattr(data, "head"):
                cols = [col for col in chain_cols if col in data.columns]
                render_table(st, data[cols].head(30) if cols else data.head(30))
            else:
                render_table(st, data)

with tabs[8]:
    st.subheader("Scenario Monitor")
    if scenario_rows is not None:
        render_table(st, scenario_rows)
    st.caption(f"Provider: {select_ai_provider(selected_ai).provider} | Model: {select_ai_provider(selected_ai).model}")
    context = {
        "symbol": symbol,
        "snapshot": snapshot,
        "scenario_rows": scenario_rows.head(20).to_dict(orient="records") if hasattr(scenario_rows, "head") else scenario_rows,
        "pressure_map": pressure_map.head(20).to_dict(orient="records") if hasattr(pressure_map, "head") else pressure_map,
        "source_status": [status.to_dict() for status in statuses if status is not None],
        "data_gaps": snapshot.get("data_gaps"),
    }
    if show_prompt_context:
        with st.expander("Prompt context", expanded=False):
            st.json(redact_secrets(str(context)))
    if st.button("Generate Neutral AI Summary"):
        response = analyze_crypto_neutral(context, preferred=selected_ai)
        st.markdown(response.text)
        st.caption(f"{response.provider} | {response.model} | {response.latency_ms} ms")

with tabs[9]:
    st.subheader("Data Status")
    optional = [
        _optional_provider_status("CoinGlass"),
        _optional_provider_status("Glassnode"),
        _optional_provider_status("CryptoQuant"),
        _optional_provider_status("Santiment"),
        _optional_provider_status("Kaiko"),
    ]
    rows = provider_status_table(statuses + optional)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    freshness_table = source_freshness_table(statuses + optional)
    freshness_fig, _, freshness_status = _source_freshness_chart(freshness_table)
    if freshness_fig is not None:
        st.plotly_chart(freshness_fig, use_container_width=True)
    render_status(st, freshness_status)
    if show_raw_status:
        st.json([status.to_dict() for status in statuses if status is not None])

page_footer(st)
