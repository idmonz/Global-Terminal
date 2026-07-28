from __future__ import annotations

from typing import Any

from .bond_data import build_bond_proxy_metrics
from .data_status import failure, success
from .global_markets import CROSS_ASSET_TICKERS, CRYPTO_MARKETS, SECTOR_ETFS
from .heatmaps import load_static_constituents
from .market_data import fetch_multi_history
from .technical_analysis import compute_rsi

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


COMMODITY_PROXIES = [
    {"ticker": "GLD", "name": "Gold ETF", "asset_class": "precious metals", "macro_sensitivity": "real rates / USD"},
    {"ticker": "SLV", "name": "Silver ETF", "asset_class": "precious metals", "macro_sensitivity": "industrial + real rates"},
    {"ticker": "USO", "name": "WTI Oil ETF", "asset_class": "energy", "macro_sensitivity": "oil balance / geopolitics"},
    {"ticker": "BNO", "name": "Brent Oil ETF", "asset_class": "energy", "macro_sensitivity": "global crude balance"},
    {"ticker": "UNG", "name": "Natural Gas ETF", "asset_class": "energy", "macro_sensitivity": "weather / storage"},
    {"ticker": "DBA", "name": "Agriculture ETF", "asset_class": "agriculture", "macro_sensitivity": "weather / food inflation"},
    {"ticker": "CPER", "name": "Copper ETF", "asset_class": "industrial metals", "macro_sensitivity": "global growth"},
    {"ticker": "CORN", "name": "Corn ETF", "asset_class": "agriculture", "macro_sensitivity": "weather / crop cycle"},
    {"ticker": "WEAT", "name": "Wheat ETF", "asset_class": "agriculture", "macro_sensitivity": "weather / geopolitics"},
    {"ticker": "SOYB", "name": "Soybean ETF", "asset_class": "agriculture", "macro_sensitivity": "weather / trade flow"},
]

SCREENER_SOURCE_MODES = ["Auto", "Native only", "OpenBB preferred", "OpenBB only"]


def normalize_screener_source_mode(source_mode: str | None = None) -> str:
    lookup = {mode.lower(): mode for mode in SCREENER_SOURCE_MODES}
    return lookup.get(str(source_mode or "Auto").strip().lower(), "Auto")


def _empty(source: str, error: str):
    if pd is None:
        return [], failure(source=source, provider="screeners", error="pandas is not installed")
    return pd.DataFrame(), failure(source=source, provider="screeners", error=error)


def _history_for(history, ticker: str):
    if pd is None or history is None or getattr(history, "empty", True):
        return None
    try:
        if isinstance(history.columns, pd.MultiIndex) and ticker in history.columns.get_level_values(0):
            return history[ticker]
        return history
    except Exception:
        return None


def _metric_row(meta: dict[str, Any], history) -> dict[str, Any]:
    ticker = meta.get("ticker")
    row = dict(meta)
    frame = _history_for(history, ticker)
    close = None
    volume = None
    if frame is not None and not getattr(frame, "empty", True):
        close_col = "Adj Close" if "Adj Close" in frame.columns else "Close" if "Close" in frame.columns else None
        if close_col:
            close = frame[close_col].dropna()
        if "Volume" in frame.columns:
            volume = frame["Volume"].dropna()
    if close is None or len(close) < 2:
        row.update(
            {
                "price": None,
                "return_1d_pct": None,
                "return_1w_pct": None,
                "return_1m_pct": None,
                "return_ytd_pct": None,
                "realized_volatility_pct": None,
                "drawdown_pct": None,
                "rsi": None,
                "price_vs_sma20_pct": None,
                "above_20dma": None,
                "above_50dma": None,
                "above_200dma": None,
                "volume_zscore": None,
                "range_52w_position": None,
                "market_data_as_of": None,
                "momentum_bucket": "Data gap",
                "volatility_bucket": "Data gap",
                "data_status": "price data unavailable",
            }
        )
        return row
    returns = close.pct_change().dropna()
    ytd = None
    try:
        year_rows = close[close.index.year == close.index[-1].year]
        ytd = float((close.iloc[-1] / year_rows.iloc[0] - 1) * 100) if len(year_rows) > 1 else None
    except Exception:
        ytd = None
    rsi_series = compute_rsi(close)
    vol_z = None
    if volume is not None and len(volume) > 20:
        recent = volume.iloc[-1]
        std = volume.tail(60).std()
        vol_z = float((recent - volume.tail(60).mean()) / std) if std else None
    high = close.tail(252).max()
    low = close.tail(252).min()
    range_pos = float((close.iloc[-1] - low) / (high - low) * 100) if high != low else None
    return_1m = float((close.iloc[-1] / close.iloc[-22] - 1) * 100) if len(close) > 22 else None
    volatility = float(returns.std() * (252**0.5) * 100) if not returns.empty else None
    sma20 = float(close.tail(20).mean()) if len(close) >= 20 else None
    market_data_as_of = None
    try:
        market_data_as_of = close.index[-1].isoformat()
    except Exception:
        market_data_as_of = str(close.index[-1])
    row.update(
        {
            "price": float(close.iloc[-1]),
            "return_1d_pct": float((close.iloc[-1] / close.iloc[-2] - 1) * 100),
            "return_1w_pct": float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) > 6 else None,
            "return_1m_pct": return_1m,
            "return_ytd_pct": ytd,
            "realized_volatility_pct": volatility,
            "drawdown_pct": float((close.iloc[-1] / close.cummax().iloc[-1] - 1) * 100),
            "rsi": float(rsi_series.dropna().iloc[-1]) if rsi_series is not None and not rsi_series.dropna().empty else None,
            "price_vs_sma20_pct": float((close.iloc[-1] / sma20 - 1) * 100) if sma20 else None,
            "above_20dma": bool(close.iloc[-1] > sma20) if sma20 else None,
            "above_50dma": bool(close.iloc[-1] > close.tail(50).mean()) if len(close) >= 50 else None,
            "above_200dma": bool(close.iloc[-1] > close.tail(200).mean()) if len(close) >= 200 else None,
            "volume_zscore": vol_z,
            "range_52w_position": range_pos,
            "market_data_as_of": market_data_as_of,
            "momentum_bucket": "High momentum" if return_1m is not None and return_1m > 8 else "Weak momentum" if return_1m is not None and return_1m < -8 else "Mixed momentum",
            "volatility_bucket": "Elevated volatility" if volatility is not None and volatility > 35 else "Moderate volatility",
            "data_status": "real/delayed yfinance",
        }
    )
    return row


def _build_from_rows(rows: list[dict[str, Any]], *, source: str, period: str = "1y"):
    if pd is None:
        return _empty(source, "pandas is not installed")
    tickers = [row["ticker"] for row in rows if row.get("ticker")]
    history, status = fetch_multi_history(tickers, period=period)
    frame = pd.DataFrame([_metric_row(row, history) for row in rows])
    return frame, status if status is not None else success(frame, source=source, provider="screeners", is_estimated=True)


def build_stock_screener(period: str = "1y"):
    constituents, static_status = load_static_constituents("sp500")
    if pd is None or getattr(constituents, "empty", True):
        return _empty("stock screener", "static stock universe unavailable")
    rows = constituents.head(80).to_dict(orient="records")
    frame, status = _build_from_rows(rows, source="stock screener", period=period)
    frame["market_cap"] = frame.get("market_cap")
    frame["valuation_bucket"] = "Data gap"
    frame["fundamental_quality"] = "Data gap"
    frame["crowding_risk"] = frame["volume_zscore"].apply(lambda value: "Elevated volume proxy" if value is not None and value > 2 else "Normal volume proxy")
    return frame, status


def build_etf_screener(period: str = "1y"):
    rows = [
        {"ticker": item["ticker"], "name": item["name"], "asset_class": item.get("sector", "sector"), "expense_ratio": None, "aum": None}
        for item in SECTOR_ETFS
    ]
    return _build_from_rows(rows, source="ETF screener", period=period)


def build_crypto_screener(period: str = "1y"):
    rows = [{"ticker": item["ticker"], "name": item["name"], "asset_class": item.get("category", "crypto")} for item in CRYPTO_MARKETS]
    frame, status = _build_from_rows(rows, source="crypto screener", period=period)
    frame["funding"] = None
    frame["open_interest_change"] = None
    frame["taker_ratio"] = None
    frame["tvl_category"] = "Data gap"
    return frame, status


def build_bond_rates_screener(period: str = "1y"):
    return build_bond_proxy_metrics(period=period)


def build_commodity_screener(period: str = "1y"):
    return _build_from_rows(COMMODITY_PROXIES, source="commodity screener", period=period)


def build_cross_asset_screener(period: str = "1y"):
    rows = [{"ticker": item["ticker"], "name": item["name"], "asset_class": item.get("asset_class", "cross-asset")} for item in CROSS_ASSET_TICKERS]
    return _build_from_rows(rows, source="cross-asset screener", period=period)


def build_screener_with_source_mode(asset_class: str, *, period: str = "1y", source_mode: str = "Auto"):
    builders = {
        "Stocks": build_stock_screener,
        "ETFs": build_etf_screener,
        "Crypto": build_crypto_screener,
        "Bonds / Rates": build_bond_rates_screener,
        "Commodities": build_commodity_screener,
        "Cross-asset": build_cross_asset_screener,
    }
    builder = builders.get(asset_class, build_stock_screener)
    native_frame, native_status = builder(period=period)
    mode = normalize_screener_source_mode(source_mode)
    from .openbb_screener_backend import build_openbb_screener_or_fallback

    return build_openbb_screener_or_fallback(native_frame, native_status, asset_class=asset_class, source_mode=mode)


def build_unified_screener_backend(asset_class: str = "Stocks", *, period: str = "1y", source_mode: str = "Auto"):
    from .openbb_screener_backend import enrich_screener_factor_scores

    frame, status, source_status = build_screener_with_source_mode(asset_class, period=period, source_mode=source_mode)
    enriched = enrich_screener_factor_scores(frame)
    source_status = {
        **source_status,
        "factor_backend": "unified",
        "factor_coverage_avg": float(enriched["factor_coverage_score"].mean()) if pd is not None and not enriched.empty and "factor_coverage_score" in enriched.columns else 0.0,
        "caveat": "Screener scores are neutral research/watchlist fields, not directives.",
    }
    return enriched, status, source_status


def apply_screener_filters(frame, *, min_return_1m: float | None = None, max_volatility: float | None = None, sector: str | None = None):
    if pd is None or frame is None or getattr(frame, "empty", True):
        return frame
    filtered = frame.copy()
    if min_return_1m is not None and "return_1m_pct" in filtered.columns:
        filtered = filtered[filtered["return_1m_pct"].fillna(-10**9) >= min_return_1m]
    if max_volatility is not None and "realized_volatility_pct" in filtered.columns:
        filtered = filtered[filtered["realized_volatility_pct"].fillna(10**9) <= max_volatility]
    if sector and "sector" in filtered.columns:
        filtered = filtered[filtered["sector"].fillna("").astype(str) == sector]
    return filtered


def build_screener_visual_summary(frame):
    if pd is None or frame is None or getattr(frame, "empty", True):
        empty = pd.DataFrame() if pd is not None else []
        return {
            "summary": {"row_count": 0, "median_return": None, "median_volatility": None, "method": "screener visual summary"},
            "result_cards": [],
            "heatmap_frame": empty,
            "scatter_frame": empty,
        }
    output = frame.copy()
    return_col = "return_1m_pct" if "return_1m_pct" in output.columns else "return_period_pct" if "return_period_pct" in output.columns else None
    vol_col = "realized_volatility_pct" if "realized_volatility_pct" in output.columns else "volatility_pct" if "volatility_pct" in output.columns else None
    momentum = output[return_col].fillna(0) if return_col else pd.Series(0, index=output.index)
    volatility = output[vol_col].fillna(0) if vol_col else pd.Series(0, index=output.index)
    output["visual_rank_score"] = (momentum.rank(pct=True) * 65 + (100 - volatility.rank(pct=True) * 100) * 0.35).round(1)
    output["rank_badge"] = output["visual_rank_score"].apply(lambda value: "Constructive backdrop" if value >= 70 else "Mixed evidence" if value >= 35 else "Deteriorating breadth")
    cards = []
    for row in output.sort_values("visual_rank_score", ascending=False).head(12).to_dict(orient="records"):
        cards.append(
            {
                "ticker": row.get("ticker"),
                "name": row.get("name"),
                "rank_badge": row.get("rank_badge"),
                "visual_rank_score": row.get("visual_rank_score"),
                "source_status": row.get("data_status", "unknown"),
                "method": "heuristic visual rank",
            }
        )
    return {
        "summary": {
            "row_count": int(len(output)),
            "median_return": float(output[return_col].median()) if return_col else None,
            "median_volatility": float(output[vol_col].median()) if vol_col else None,
            "method": "screener visual summary",
        },
        "result_cards": cards,
        "heatmap_frame": output,
        "scatter_frame": output[[col for col in ["ticker", "name", "asset_class", return_col, vol_col, "visual_rank_score", "rank_badge", "data_status"] if col and col in output.columns]],
    }
