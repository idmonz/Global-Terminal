from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .config import STATIC_DIR
from .data_status import DataResult, combine_results, failure, success
from .global_markets import CROSS_ASSET_TICKERS, CRYPTO_MARKETS, G7_MARKETS, SECTOR_ETFS
from .market_data import fetch_multi_history
from .technical_analysis import compute_drawdown, compute_realized_vol, compute_regime_label

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency fallback
    pd = None


RETURN_COLUMNS = ["daily_return", "weekly_return", "monthly_return", "ytd_return"]


def _empty():
    return [] if pd is None else pd.DataFrame()


def _ensure_display_columns(data):
    if pd is None or data is None or getattr(data, "empty", True):
        return data
    frame = data.copy()
    if "name" not in frame.columns:
        if "company" in frame.columns:
            frame["name"] = frame["company"].fillna(frame.get("ticker", "Unknown"))
        elif "ticker" in frame.columns:
            frame["name"] = frame["ticker"]
        else:
            frame["name"] = "Unknown"
    if "group" not in frame.columns:
        if "sector" in frame.columns:
            frame["group"] = frame["sector"].fillna("Market")
        else:
            frame["group"] = "Market"
    return frame


def load_static_constituents(name: str) -> tuple[object, DataResult]:
    path = STATIC_DIR / "index_constituents" / f"{name}.csv"
    if pd is None:
        return _empty(), failure(source=str(path), provider="static", error="pandas is not installed")
    if not path.exists():
        return pd.DataFrame(), failure(source=str(path), provider="static", error="Static constituent file is missing")
    try:
        data = _ensure_display_columns(pd.read_csv(path))
        return data, success(data, source=str(path), provider="static", stale_after_seconds=86400 * 30, coverage=f"{len(data)} static rows")
    except Exception as exc:
        return pd.DataFrame(), failure(source=str(path), provider="static", error=str(exc))


def _history_for_ticker(history, ticker: str):
    if pd is None or history is None or getattr(history, "empty", True):
        return None
    if isinstance(history.columns, pd.MultiIndex):
        if ticker in history.columns.get_level_values(0):
            return history[ticker].dropna(how="all")
        return None
    return history.dropna(how="all")


def pct_from_offset(close, offset: int) -> float | None:
    if close is None or len(close) <= offset:
        return None
    base = close.iloc[-offset - 1]
    if not base:
        return None
    return float((close.iloc[-1] / base - 1) * 100)


def _returns_from_single_history(frame) -> dict[str, float | None]:
    if pd is None or frame is None or getattr(frame, "empty", True):
        return {column: None for column in RETURN_COLUMNS} | {
            "price": None,
            "volume": None,
            "realized_vol": None,
            "drawdown_52w": None,
            "regime": "data unavailable",
        }
    close_col = "Adj Close" if "Adj Close" in frame.columns else "Close" if "Close" in frame.columns else None
    if close_col is None:
        return {column: None for column in RETURN_COLUMNS} | {
            "price": None,
            "volume": None,
            "realized_vol": None,
            "drawdown_52w": None,
            "regime": "data unavailable",
        }
    close = frame[close_col].dropna()
    if close.empty:
        return {column: None for column in RETURN_COLUMNS} | {
            "price": None,
            "volume": None,
            "realized_vol": None,
            "drawdown_52w": None,
            "regime": "data unavailable",
        }

    ytd = None
    try:
        current_year = close.index[-1].year
        year_rows = close[close.index.year == current_year]
        if len(year_rows) > 1:
            ytd = float((close.iloc[-1] / year_rows.iloc[0] - 1) * 100)
    except Exception:
        ytd = None

    realized_vol = compute_realized_vol(close)
    drawdown = compute_drawdown(close)
    volume = frame["Volume"].dropna().iloc[-1] if "Volume" in frame.columns and not frame["Volume"].dropna().empty else None
    return {
        "price": float(close.iloc[-1]),
        "daily_return": pct_from_offset(close, 1),
        "weekly_return": pct_from_offset(close, 5),
        "monthly_return": pct_from_offset(close, 21),
        "ytd_return": ytd,
        "volume": float(volume) if volume is not None else None,
        "realized_vol": float(realized_vol.dropna().iloc[-1] * 100) if realized_vol is not None and not realized_vol.dropna().empty else None,
        "drawdown_52w": float(drawdown.dropna().iloc[-1] * 100) if drawdown is not None and not drawdown.dropna().empty else None,
        "regime": compute_regime_label(close),
    }


def enrich_with_yfinance_rows(rows: object, *, ticker_col: str = "ticker", period: str = "1y") -> tuple[object, DataResult]:
    if pd is None:
        return rows, failure(source="market rows", provider="yfinance", error="pandas is not installed")
    if rows is None or rows.empty:
        return pd.DataFrame(), failure(source="market rows", provider="yfinance", error="No rows supplied")
    tickers = rows[ticker_col].dropna().astype(str).tolist()
    history, status = fetch_multi_history(tickers, period=period)
    enriched = _ensure_display_columns(rows)
    metrics = []
    for ticker in tickers:
        metrics.append({"ticker": ticker, **_returns_from_single_history(_history_for_ticker(history, ticker))})
    metrics_df = pd.DataFrame(metrics)
    if not metrics_df.empty:
        enriched = enriched.merge(metrics_df, how="left", on="ticker")
    if "market_cap" not in enriched.columns:
        enriched["market_cap"] = 1
    enriched["size_value"] = enriched["market_cap"].fillna(1).astype(float).clip(lower=1)
    enriched["data_quality"] = "real/delayed" if status.ok else "data unavailable"
    return _ensure_display_columns(enriched), status


def build_sp500_heatmap() -> tuple[object, DataResult]:
    constituents, static_status = load_static_constituents("sp500")
    if pd is None:
        return constituents, static_status
    data, live_status = enrich_with_yfinance_rows(constituents)
    combined = combine_results([static_status, live_status], provider="heatmaps", source="S&P 500 static + yfinance")
    return data, combined


def build_nasdaq100_heatmap() -> tuple[object, DataResult]:
    constituents, static_status = load_static_constituents("nasdaq100")
    if pd is None:
        return constituents, static_status
    data, live_status = enrich_with_yfinance_rows(constituents)
    combined = combine_results([static_status, live_status], provider="heatmaps", source="Nasdaq 100 static + yfinance")
    return data, combined


def build_korea_heatmap() -> tuple[object, DataResult]:
    constituents, static_status = load_static_constituents("korea_watchlist")
    if pd is None:
        return constituents, static_status
    data, live_status = enrich_with_yfinance_rows(constituents)
    combined = combine_results([static_status, live_status], provider="heatmaps", source="Korea static + yfinance fallback")
    return data, combined


def _rows_from_universe(items: Iterable[dict], *, parent_key: str, label_key: str = "name") -> object:
    if pd is None:
        return []
    rows = []
    for item in items:
        row = dict(item)
        row["name"] = item.get(label_key) or item.get("ticker")
        row["group"] = item.get(parent_key, "Market")
        row["market_cap"] = item.get("market_cap", 1)
        rows.append(row)
    return pd.DataFrame(rows)


def build_sector_heatmap() -> tuple[object, DataResult]:
    if pd is None:
        return [], failure(source="sector ETFs", provider="static", error="pandas is not installed")
    rows = _rows_from_universe(SECTOR_ETFS, parent_key="sector")
    data, status = enrich_with_yfinance_rows(rows, period="1y")
    if not getattr(data, "empty", True):
        data["above_50dma_pct"] = None
        data["above_200dma_pct"] = None
        data["breadth"] = "ETF proxy"
    return data, status


def build_g7_heatmap() -> tuple[object, DataResult]:
    if pd is None:
        return [], failure(source="G7 markets", provider="static", error="pandas is not installed")
    rows = pd.DataFrame(
        {
            "ticker": item["index"],
            "name": item["country"],
            "country": item["country"],
            "group": "G7 + Korea",
            "etf_proxy": item["etf"],
            "currency": item["currency"],
            "fx_ticker": item["fx"],
            "yield_10y": item["yield_10y"],
            "market_cap": 1,
        }
        for item in G7_MARKETS
    )
    return enrich_with_yfinance_rows(rows, period="1y")


def build_cross_asset_heatmap() -> tuple[object, DataResult]:
    if pd is None:
        return [], failure(source="cross asset", provider="static", error="pandas is not installed")
    rows = _rows_from_universe(CROSS_ASSET_TICKERS, parent_key="asset_class")
    return enrich_with_yfinance_rows(rows, period="1y")


def build_crypto_heatmap() -> tuple[object, DataResult]:
    if pd is None:
        return [], failure(source="crypto", provider="static", error="pandas is not installed")
    rows = _rows_from_universe(CRYPTO_MARKETS, parent_key="category")
    return enrich_with_yfinance_rows(rows, period="1y")
