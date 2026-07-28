from __future__ import annotations

from typing import Any

from .crypto_scenarios import estimate_liquidation_pressure_map
from .data_status import combine_results, failure, success
from .energy_data import get_eia_api_key_status, get_yfinance_energy_fallback
from .equity_breadth import compute_index_breadth_snapshot
from .global_markets import CROSS_ASSET_TICKERS, CRYPTO_MARKETS, SECTOR_ETFS
from .heatmaps import build_cross_asset_heatmap, build_crypto_heatmap, build_sector_heatmap
from .map_viz import build_chokepoint_map
from .market_radar import (
    build_cross_asset_radar,
    build_crypto_derivatives_radar,
    build_energy_risk_radar,
    build_equity_breadth_radar,
    build_market_composite_score,
    build_volatility_radar,
)
from .market_data import fetch_history, fetch_multi_history
from .signal_fusion import build_signal_convergence_table, fuse_crypto_signals, fuse_energy_signals, fuse_market_signals
from .source_freshness import source_freshness_table
from .technical_analysis import compute_drawdown, compute_realized_vol
from .worldmonitor_adapter import check_worldmonitor_status

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


OVERVIEW_ASSETS = [
    {"label": "S&P 500", "ticker": "^GSPC"},
    {"label": "Nasdaq 100", "ticker": "^NDX"},
    {"label": "Dow", "ticker": "^DJI"},
    {"label": "Russell 2000", "ticker": "^RUT"},
    {"label": "VIX", "ticker": "^VIX"},
    {"label": "US 10Y", "ticker": "^TNX"},
    {"label": "DXY", "ticker": "DX-Y.NYB"},
    {"label": "Gold", "ticker": "GC=F"},
    {"label": "WTI", "ticker": "CL=F"},
    {"label": "BTC", "ticker": "BTC-USD"},
    {"label": "ETH", "ticker": "ETH-USD"},
    {"label": "KOSPI", "ticker": "^KS11"},
]


def _close(frame):
    if frame is None or getattr(frame, "empty", True):
        return None
    close_col = "Adj Close" if "Adj Close" in frame.columns else "Close" if "Close" in frame.columns else None
    if close_col is None:
        return None
    series = frame[close_col]
    if isinstance(series, pd.DataFrame):
        series = series.squeeze(axis=1) if series.shape[1] == 1 else series.iloc[:, 0]
    series = pd.to_numeric(series, errors="coerce").dropna()
    return series if not series.empty else None


def _history_slice(history, ticker: str):
    if pd is None or history is None or getattr(history, "empty", True):
        return None
    try:
        if isinstance(history.columns, pd.MultiIndex) and ticker in history.columns.get_level_values(0):
            return history[ticker].dropna(how="all")
        return history.dropna(how="all")
    except Exception:
        return None


def _flatten_history_columns(frame, ticker: str | None = None):
    if pd is None or frame is None or getattr(frame, "empty", True):
        return frame
    if not isinstance(frame.columns, pd.MultiIndex):
        return frame
    try:
        if ticker and ticker in frame.columns.get_level_values(0):
            return frame[ticker].copy()
        last_level = frame.columns.nlevels - 1
        if ticker and ticker in frame.columns.get_level_values(last_level):
            return frame.xs(ticker, axis=1, level=last_level).copy()
        if len(frame.columns.get_level_values(last_level).unique()) == 1:
            return frame.droplevel(last_level, axis=1).copy()
        if len(frame.columns.get_level_values(0).unique()) == 1:
            return frame.droplevel(0, axis=1).copy()
    except Exception:
        return frame
    return frame


def build_cross_asset_cards(period: str = "6mo"):
    if pd is None:
        return [], failure(source="overview cards", provider="overview", error="pandas is not installed")
    tickers = [item["ticker"] for item in OVERVIEW_ASSETS]
    history, status = fetch_multi_history(tickers, period=period)
    rows = []
    for item in OVERVIEW_ASSETS:
        frame = _history_slice(history, item["ticker"])
        close = _close(frame)
        if close is not None and len(close) > 1:
            returns = close.pct_change().dropna()
            realized_vol = float(returns.std() * (252**0.5) * 100) if not returns.empty else None
            return_1m = float((close.iloc[-1] / close.iloc[-22] - 1) * 100) if len(close) > 22 else None
            rows.append(
                {
                    **item,
                    "price": float(close.iloc[-1]),
                    "change_pct": float((close.iloc[-1] / close.iloc[-2] - 1) * 100),
                    "return_1m_pct": return_1m,
                    "period_return_pct": float((close.iloc[-1] / close.iloc[0] - 1) * 100),
                    "realized_volatility_pct": realized_vol,
                    "volatility_regime": "Elevated volatility" if realized_vol is not None and realized_vol >= 30 else "Mixed evidence",
                    "sparkline": [float(value) for value in close.tail(28).tolist()],
                    "data_status": "real/delayed yfinance",
                }
            )
        else:
            rows.append(
                {
                    **item,
                    "price": None,
                    "change_pct": None,
                    "return_1m_pct": None,
                    "period_return_pct": None,
                    "realized_volatility_pct": None,
                    "volatility_regime": "Data gap",
                    "sparkline": [],
                    "data_status": "data gap",
                }
            )
    return pd.DataFrame(rows), status


def build_main_asset_chart_data(ticker: str, period: str = "1y"):
    history, status = fetch_history(ticker, period=period)
    if pd is not None and history is not None and not getattr(history, "empty", True):
        frame = _flatten_history_columns(history.copy(), ticker)
        close = _close(frame)
        if close is not None:
            frame["performance_pct"] = (close / close.iloc[0] - 1) * 100
            drawdown = compute_drawdown(close)
            realized_vol = compute_realized_vol(close)
            if drawdown is not None:
                frame["drawdown_pct"] = drawdown * 100
            if realized_vol is not None:
                frame["realized_volatility_pct"] = realized_vol * 100
        return frame, status
    return history, status


def build_crypto_mini_panel():
    if pd is None:
        return {}, failure(source="crypto mini panel", provider="overview", error="pandas is not installed")
    tickers = [item["ticker"] for item in CRYPTO_MARKETS[:3]]
    history, status = fetch_multi_history(tickers, period="3mo")
    btc_frame = _history_slice(history, "BTC-USD")
    close = _close(btc_frame)
    pressure, pressure_status = estimate_liquidation_pressure_map(klines=None, snapshot={"current_price": float(close.iloc[-1]) if close is not None else None})
    panel = {
        "btc_price": float(close.iloc[-1]) if close is not None else None,
        "open_interest": None,
        "funding": None,
        "taker_ratio": None,
        "long_short_ratio": None,
        "liquidation_pressure_summary": "Estimated pressure map available" if not getattr(pressure, "empty", True) else "data gap",
        "stablecoin_tvl_snapshot": "DefiLlama optional panel available on Crypto Intelligence page",
        "data_gaps": ["Binance derivatives not auto-called on overview"],
    }
    return panel, combine_results([status, pressure_status], provider="overview", source="crypto mini panel")


def build_equity_mini_panel():
    try:
        snapshot, status = compute_index_breadth_snapshot()
        return snapshot, status
    except Exception as exc:
        return {
            "breadth": None,
            "above_50dma_pct": None,
            "above_200dma_pct": None,
            "advance_decline": None,
            "sector_participation": "data gap",
            "unusual_volume_proxy": "data gap",
        }, failure(source="equity mini panel", provider="overview", error=str(exc), is_estimated=True)


def build_energy_geopolitical_mini_panel():
    prices, price_status = get_yfinance_energy_fallback(period="3mo")
    eia_status = get_eia_api_key_status()
    wm_status = check_worldmonitor_status()
    status_inputs = [price_status, eia_status]
    if wm_status.ok:
        status_inputs.append(wm_status)
    panel = {
        "wti_brent": prices,
        "inventory_status": "EIA key available" if eia_status.ok else "EIA optional key unavailable",
        "chokepoint_risk_proxy": "Static chokepoint registry with optional WorldMonitor adapter",
        "latest_headlines": "Use News / Energy pages for GDELT/RSS pull",
        "worldmonitor_adapter_status": wm_status.to_dict(),
    }
    status = combine_results(status_inputs, provider="overview", source="energy/geopolitical mini panel")
    return panel, status


def build_risk_mini_panel(cards=None):
    rows = cards if cards is not None else None
    vix = None
    if pd is not None and rows is not None and hasattr(rows, "loc") and "label" in rows.columns:
        match = rows.loc[rows["label"] == "VIX"]
        if not match.empty:
            vix = match.iloc[0].get("price")
    panel = {
        "vix": vix,
        "cross_asset_volatility_regime": "Elevated volatility" if vix is not None and vix > 25 else "Mixed / normal volatility",
        "correlation_stress": "Use Risk Lab for rolling correlation matrix",
        "var_snapshot": "VaR requires selected basket return history",
        "risk_scenario_badges": ["volatility regime", "correlation stress", "liquidity watch"],
    }
    return panel, success(panel, source="overview risk mini panel", provider="overview", is_estimated=True, coverage="proxy risk diagnostics")


def build_heatmap_strip():
    sectors, sector_status = build_sector_heatmap()
    crypto, crypto_status = build_crypto_heatmap()
    cross_asset, cross_status = build_cross_asset_heatmap()
    return {
        "sectors": sectors,
        "crypto": crypto,
        "cross_asset": cross_asset,
    }, combine_results([sector_status, crypto_status, cross_status], provider="overview", source="overview heatmap strip")


def build_event_news_map():
    fig, frame, status = build_chokepoint_map()
    timeline = frame[["name", "region", "risk_proxy", "source_status"]] if pd is not None and hasattr(frame, "columns") else frame
    return {"map": fig, "events": frame, "timeline": timeline}, status


def build_overview_terminal_data(selected_ticker: str = "SPY", period: str = "1y") -> tuple[dict[str, Any], Any]:
    cards, cards_status = build_cross_asset_cards(period="6mo")
    chart, chart_status = build_main_asset_chart_data(selected_ticker, period=period)
    heatmaps, heatmap_status = build_heatmap_strip()
    crypto, crypto_status = build_crypto_mini_panel()
    equity, equity_status = build_equity_mini_panel()
    energy, energy_status = build_energy_geopolitical_mini_panel()
    risk, risk_status = build_risk_mini_panel(cards)
    event_map, event_status = build_event_news_map()
    cross_asset_radar = build_cross_asset_radar(cards)
    equity_radar = build_equity_breadth_radar(equity if isinstance(equity, dict) else {})
    crypto_radar = build_crypto_derivatives_radar(crypto if isinstance(crypto, dict) else {})
    energy_radar = build_energy_risk_radar(energy if isinstance(energy, dict) else {})
    volatility_radar = build_volatility_radar(risk, cards)
    composite = build_market_composite_score(cross_asset_radar, equity_radar, crypto_radar, energy_radar, volatility_radar)
    market_signal = fuse_market_signals(cards=cards)
    crypto_signal = fuse_crypto_signals(crypto if isinstance(crypto, dict) else {}, crypto_radar)
    energy_signal = fuse_energy_signals(energy if isinstance(energy, dict) else {})
    signal_convergence = build_signal_convergence_table([market_signal, crypto_signal, energy_signal])
    source_statuses = [cards_status, chart_status, heatmap_status, crypto_status, equity_status, energy_status, risk_status, event_status]
    payload = {
        "cards": cards,
        "chart": chart,
        "heatmaps": heatmaps,
        "crypto": crypto,
        "equity": equity,
        "energy": energy,
        "risk": risk,
        "event_map": event_map,
        "market_radar": {
            "cross_asset": cross_asset_radar,
            "equity": equity_radar,
            "crypto": crypto_radar,
            "energy": energy_radar,
            "volatility": volatility_radar,
            "composite": composite,
        },
        "signal_convergence": signal_convergence,
        "source_statuses": source_statuses,
        "source_freshness": source_freshness_table(source_statuses),
        "data_gaps": [
            "LLM analysis is button-triggered only.",
            "WorldMonitor adapter is optional and not required at runtime.",
            "AIS and dealer-confirmed gamma exposure are unavailable without providers.",
        ],
    }
    status = combine_results(payload["source_statuses"], provider="overview", source="overview terminal")
    return payload, status
