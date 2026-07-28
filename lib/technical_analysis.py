from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _series(values) -> pd.Series:
    if isinstance(values, pd.Series):
        return pd.to_numeric(values, errors="coerce")
    if isinstance(values, pd.DataFrame):
        for column in ["close", "Close", "Adj Close"]:
            if column in values.columns:
                selected = values[column]
                if isinstance(selected, pd.DataFrame):
                    selected = selected.squeeze(axis=1) if selected.shape[1] == 1 else selected.iloc[:, 0]
                return pd.to_numeric(selected, errors="coerce")
        if values.shape[1] == 1:
            return pd.to_numeric(values.iloc[:, 0], errors="coerce")
        numeric = values.apply(pd.to_numeric, errors="coerce")
        usable = numeric.dropna(axis=1, how="all")
        if not usable.empty:
            return usable.iloc[:, 0]
        return pd.Series(dtype="float64")
    try:
        if hasattr(values, "ndim") and getattr(values, "ndim") == 2:
            values = values.squeeze()
    except Exception:
        pass
    return pd.to_numeric(pd.Series(values), errors="coerce")


def compute_returns(prices, periods: int = 1) -> pd.Series:
    return _series(prices).pct_change(periods=periods)


def compute_rsi(prices, window: int = 14) -> pd.Series:
    close = _series(prices)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    result = result.mask((loss == 0) & (gain > 0), 100.0)
    result = result.mask((loss == 0) & (gain == 0), 50.0)
    return result


def compute_macd(prices, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    close = _series(prices)
    fast_ema = close.ewm(span=fast, adjust=False).mean()
    slow_ema = close.ewm(span=slow, adjust=False).mean()
    macd = fast_ema - slow_ema
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({"macd": macd, "signal": signal_line, "histogram": macd - signal_line})


def compute_atr(data, low=None, close=None, window: int = 14) -> pd.Series:
    if low is not None and close is not None:
        high = pd.to_numeric(pd.Series(data), errors="coerce")
        low = pd.to_numeric(pd.Series(low), errors="coerce")
        close = pd.to_numeric(pd.Series(close), errors="coerce")
    else:
        frame = data.copy()
        high = pd.to_numeric(frame.get("high", frame.get("High")), errors="coerce")
        low = pd.to_numeric(frame.get("low", frame.get("Low")), errors="coerce")
        close = pd.to_numeric(frame.get("close", frame.get("Close")), errors="coerce")
    prev_close = close.shift(1)
    true_range = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return true_range.rolling(window).mean()


def compute_bollinger(prices, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    close = _series(prices)
    middle = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    position = (close - lower) / (upper - lower).replace(0, np.nan)
    return pd.DataFrame({"middle": middle, "upper": upper, "lower": lower, "position": position})


def compute_sma_ema(prices, windows: tuple[int, ...] = (20, 50, 100, 200)) -> pd.DataFrame:
    close = _series(prices)
    data = {}
    for window in windows:
        data[f"sma_{window}"] = close.rolling(window).mean()
        data[f"ema_{window}"] = close.ewm(span=window, adjust=False).mean()
    return pd.DataFrame(data)


def compute_drawdown(prices) -> pd.Series:
    close = _series(prices)
    running_max = close.cummax()
    return close / running_max - 1


def compute_realized_vol(prices_or_returns, window: int = 20, annualization: int = 252) -> pd.Series:
    series = _series(prices_or_returns)
    returns = series if series.abs().max(skipna=True) < 1 else series.pct_change()
    return returns.rolling(window).std() * math.sqrt(annualization)


def compute_volume_zscore(volume, window: int = 20) -> pd.Series:
    series = pd.to_numeric(pd.Series(volume), errors="coerce")
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    return (series - mean) / std.replace(0, np.nan)


def compute_pivot_levels(data: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    frame = data.copy()
    high = pd.to_numeric(frame.get("high", frame.get("High")), errors="coerce")
    low = pd.to_numeric(frame.get("low", frame.get("Low")), errors="coerce")
    close = pd.to_numeric(frame.get("close", frame.get("Close")), errors="coerce")
    pivot = (high.rolling(lookback).max() + low.rolling(lookback).min() + close) / 3
    return pd.DataFrame({"pivot": pivot, "support": 2 * pivot - high.rolling(lookback).max(), "resistance": 2 * pivot - low.rolling(lookback).min()})


def compute_support_resistance(data: pd.DataFrame, lookback: int = 60) -> dict[str, float | None]:
    if data is None or data.empty:
        return {"support": None, "resistance": None}
    close = _series(data).dropna().tail(lookback)
    if close.empty:
        return {"support": None, "resistance": None}
    return {"support": float(close.quantile(0.2)), "resistance": float(close.quantile(0.8))}


def compute_relative_strength(asset_prices, benchmark_prices, window: int = 63) -> pd.Series:
    asset = _series(asset_prices)
    benchmark = _series(benchmark_prices)
    ratio = asset / benchmark.reindex(asset.index).ffill()
    return ratio / ratio.rolling(window).mean() - 1


def compute_regime_label(prices) -> str:
    close = _series(prices).dropna()
    if len(close) < 50:
        return "Neutral / mixed evidence"
    sma_20 = close.rolling(20).mean().iloc[-1]
    sma_50 = close.rolling(50).mean().iloc[-1]
    last = close.iloc[-1]
    drawdown = last / close.cummax().iloc[-1] - 1
    if drawdown < -0.15:
        return "Stress condition"
    if last > sma_20 > sma_50:
        return "Constructive technical backdrop"
    if last < sma_20 < sma_50:
        return "Deteriorating momentum"
    return "Neutral / mixed evidence"


def compute_technical_score_neutral(data: pd.DataFrame) -> dict[str, float | str | None]:
    if data is None or data.empty:
        return {"score": 50.0, "label": "Data gap", "data_gap": "No price history supplied."}
    close = _series(data).dropna()
    if len(close) < 30:
        return {"score": 50.0, "label": "Neutral / mixed evidence", "data_gap": "Insufficient history."}
    rsi = compute_rsi(close).iloc[-1]
    regime = compute_regime_label(close)
    drawdown = compute_drawdown(close).iloc[-1]
    score = 50.0
    if regime == "Constructive technical backdrop":
        score += 15
    elif regime == "Deteriorating momentum":
        score -= 15
    if pd.notna(rsi):
        score += max(-15, min(15, (rsi - 50) / 2))
    score += max(-15, min(10, drawdown * 100))
    return {"score": float(max(0, min(100, score))), "label": regime, "data_gap": None}
