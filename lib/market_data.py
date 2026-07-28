from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .data_status import DataResult, failure, success

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency fallback
    pd = None

try:
    import yfinance as yf
except Exception:  # pragma: no cover - optional dependency fallback
    yf = None


def empty_frame():
    if pd is None:
        return []
    return pd.DataFrame()


def fetch_history(ticker: str, *, period: str = "6mo", interval: str = "1d") -> tuple[object, DataResult]:
    if yf is None or pd is None:
        return empty_frame(), failure(source=ticker, provider="yfinance", error="yfinance or pandas is not installed")
    try:
        data = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
            timeout=12,
        )
        if data is None or data.empty:
            return empty_frame(), failure(source=ticker, provider="yfinance", error="No rows returned")
        data.attrs["fetched_at"] = datetime.now(timezone.utc)
        return data, success(data, source=ticker, provider="yfinance", stale_after_seconds=900, is_adjusted=False)
    except Exception as exc:
        return empty_frame(), failure(source=ticker, provider="yfinance", error=str(exc))


def fetch_multi_history(tickers: Iterable[str], *, period: str = "6mo") -> tuple[object, DataResult]:
    symbols = [ticker for ticker in tickers if ticker]
    if yf is None or pd is None:
        return empty_frame(), failure(source=",".join(symbols), provider="yfinance", error="yfinance or pandas is not installed")
    if not symbols:
        return empty_frame(), failure(source="ticker list", provider="yfinance", error="No tickers supplied")
    try:
        data = yf.download(
            symbols,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=False,
            group_by="ticker",
            threads=True,
            timeout=12,
        )
        if data is None or data.empty:
            return empty_frame(), failure(source=",".join(symbols), provider="yfinance", error="No rows returned")
        data.attrs["fetched_at"] = datetime.now(timezone.utc)
        return data, success(data, source=",".join(symbols), provider="yfinance", stale_after_seconds=900, is_adjusted=False)
    except Exception as exc:
        return empty_frame(), failure(source=",".join(symbols), provider="yfinance", error=str(exc))


def latest_close(history) -> float | None:
    if pd is None or history is None or getattr(history, "empty", True):
        return None
    column = "Adj Close" if "Adj Close" in history.columns else "Close" if "Close" in history.columns else None
    if column is None:
        return None
    values = history[column]
    if hasattr(values, "columns"):
        values = values.bfill(axis=1).iloc[:, 0]
    series = values.dropna()
    if series.empty:
        return None
    return float(series.iloc[-1])


def _canonical_column_name(value) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _series_from_column(frame, column: str):
    if column not in frame.columns:
        return pd.Series(pd.NA, index=frame.index)
    values = frame[column]
    if hasattr(values, "columns"):
        values = values.bfill(axis=1).iloc[:, 0]
    return values


def normalize_ohlcv(data) -> object:
    if pd is None or data is None or getattr(data, "empty", True):
        return empty_frame()
    frame = data.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        field_names = {"open", "high", "low", "close", "adj_close", "volume"}
        field_level = 0
        for level in range(frame.columns.nlevels):
            names = {_canonical_column_name(value) for value in frame.columns.get_level_values(level)}
            if names & field_names:
                field_level = level
                break
        frame.columns = [col[field_level] if isinstance(col, tuple) else col for col in frame.columns]
    rename = {col: _canonical_column_name(col) for col in frame.columns}
    frame = frame.rename(columns=rename)
    if "date" not in frame.columns:
        frame = frame.reset_index().rename(columns={"Date": "date", "Datetime": "date", "index": "date"})
        frame = frame.rename(columns={col: _canonical_column_name(col) for col in frame.columns})
    output = pd.DataFrame(index=frame.index)
    output["date"] = _series_from_column(frame, "date")
    for col in ["open", "high", "low", "close", "volume"]:
        output[col] = _series_from_column(frame, col)
    output["adj_close"] = _series_from_column(frame, "adj_close") if "adj_close" in frame.columns else output["close"]
    for col in ["open", "high", "low", "close", "adj_close", "volume"]:
        output[col] = pd.to_numeric(output[col], errors="coerce")
    return output[["date", "open", "high", "low", "close", "adj_close", "volume"]].dropna(subset=["close"], how="all")


def fetch_price_history(ticker: str, *, period: str = "1y", interval: str = "1d") -> tuple[object, DataResult]:
    raw, status = fetch_history(ticker, period=period, interval=interval)
    return normalize_ohlcv(raw), status


def fetch_many_price_histories(tickers: Iterable[str], *, period: str = "1y") -> tuple[dict[str, object], DataResult]:
    results: dict[str, object] = {}
    statuses: list[DataResult] = []
    symbols = [ticker for ticker in tickers if ticker]
    for ticker in symbols:
        frame, status = fetch_price_history(ticker, period=period)
        statuses.append(status)
        if not getattr(frame, "empty", True):
            results[ticker] = frame
    if not statuses:
        return results, failure(source="ticker list", provider="yfinance", error="No tickers supplied")
    ok_count = sum(status.ok for status in statuses)
    if ok_count == 0:
        return results, failure(source=",".join(symbols), provider="yfinance", error="No tickers returned usable history")
    return results, success(
        results,
        source=",".join(symbols),
        provider="yfinance",
        stale_after_seconds=900,
        warning=None if ok_count == len(statuses) else "Partial ticker coverage.",
        coverage=f"{ok_count}/{len(statuses)} tickers",
        is_adjusted=False,
    )


def latest_price_snapshot(tickers: Iterable[str]) -> tuple[object, DataResult]:
    if pd is None:
        return empty_frame(), failure(source="ticker list", provider="yfinance", error="pandas is not installed")
    rows: list[dict] = []
    histories, status = fetch_many_price_histories(tickers, period="2mo")
    for ticker, frame in histories.items():
        if getattr(frame, "empty", True) or "close" not in frame.columns:
            continue
        clean = frame.dropna(subset=["close"])
        if clean.empty:
            continue
        last = clean.iloc[-1]
        prev = clean.iloc[-2] if len(clean) > 1 else last
        rows.append(
            {
                "ticker": ticker,
                "price": float(last["close"]),
                "daily_return": float(last["close"] / prev["close"] - 1) if prev["close"] else 0.0,
                "volume": float(last.get("volume", 0) or 0),
                "date": last["date"],
            }
        )
    return pd.DataFrame(rows), status
