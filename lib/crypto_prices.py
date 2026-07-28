from __future__ import annotations

from typing import Any

from .cache import fetch_json
from .crypto_derivatives import get_binance_klines, normalize_symbol
from .data_status import DataResult, combine_results, failure
from .technical_analysis import compute_atr, compute_bollinger, compute_macd, compute_realized_vol, compute_rsi, compute_volume_zscore

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


COINGECKO_PROVIDER = "CoinGecko"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
SYMBOL_TO_COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "DOGE": "dogecoin",
}


def _coingecko_get(path: str, *, params: dict[str, Any] | None = None, ttl_seconds: int = 300, source: str | None = None):
    return fetch_json(f"{COINGECKO_BASE_URL}{path}", params=params, provider=COINGECKO_PROVIDER, source=source or path, ttl_seconds=ttl_seconds, timeout=12)


def _empty_frame(columns: list[str]):
    if pd is None:
        return []
    return pd.DataFrame(columns=columns)


def get_coingecko_markets(vs_currency: str = "usd", limit: int = 100):
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": min(int(limit), 250),
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d,30d",
    }
    payload, status = _coingecko_get("/coins/markets", params=params, ttl_seconds=300, source="CoinGecko coins markets")
    columns = ["id", "symbol", "name", "current_price", "market_cap", "total_volume", "price_change_percentage_1h_in_currency", "price_change_percentage_24h", "price_change_percentage_7d_in_currency", "price_change_percentage_30d_in_currency", "market_cap_rank", "last_updated"]
    if payload is None:
        return _empty_frame(columns), status
    if not isinstance(payload, list):
        return _empty_frame(columns), failure(source="CoinGecko coins markets", provider=COINGECKO_PROVIDER, error="CoinGecko markets response was not a list.", coverage="malformed response")
    if pd is None:
        return payload, status
    frame = pd.DataFrame(payload)
    for col in columns:
        if col not in frame.columns:
            frame[col] = None
    frame = frame[columns]
    for col in ["current_price", "market_cap", "total_volume", "price_change_percentage_1h_in_currency", "price_change_percentage_24h", "price_change_percentage_7d_in_currency", "price_change_percentage_30d_in_currency"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame, status


def get_crypto_market_overview():
    markets, status = get_coingecko_markets(limit=100)
    if pd is None or getattr(markets, "empty", True):
        return {"total_market_cap": None, "total_volume": None, "asset_count": 0}, status
    overview = {
        "total_market_cap": float(markets["market_cap"].dropna().sum()),
        "total_volume": float(markets["total_volume"].dropna().sum()),
        "asset_count": int(len(markets)),
        "median_24h_change": float(markets["price_change_percentage_24h"].dropna().median()) if markets["price_change_percentage_24h"].notna().any() else None,
    }
    return overview, status


def get_crypto_coin_snapshot(coin_id_or_symbol: str):
    coin = (coin_id_or_symbol or "").strip().lower()
    coin_id = SYMBOL_TO_COINGECKO_ID.get(coin.upper(), coin)
    markets, status = get_coingecko_markets(limit=250)
    if pd is None or getattr(markets, "empty", True):
        return {}, status
    match = markets[(markets["id"].str.lower() == coin_id) | (markets["symbol"].str.lower() == coin)]
    if match.empty:
        return {}, failure(source="CoinGecko coins markets", provider=COINGECKO_PROVIDER, error=f"Coin snapshot unavailable for {coin_id_or_symbol}.", coverage="missing coin")
    return match.iloc[0].to_dict(), status


def _pct_change(frame, bars: int) -> float | None:
    if frame is None or getattr(frame, "empty", True) or len(frame) <= bars:
        return None
    start = frame["close"].iloc[-bars - 1]
    end = frame["close"].iloc[-1]
    if not start:
        return None
    return float((end / start - 1.0) * 100.0)


def get_binance_price_proxy_from_futures_klines(symbol: str, interval: str = "1h", limit: int = 200):
    klines, status = get_binance_klines(symbol, interval=interval, limit=limit)
    if pd is None or getattr(klines, "empty", True):
        return {"symbol": normalize_symbol(symbol)}, status
    close = klines["close"]
    high = klines["high"]
    low = klines["low"]
    volume = klines["volume"]
    rsi = compute_rsi(close)
    macd, macd_signal, macd_hist = compute_macd(close)
    atr = compute_atr(high, low, close)
    realized = compute_realized_vol(close, window=min(24, max(2, len(close) // 4)), annualization=365 * 24)
    volume_z = compute_volume_zscore(volume, window=min(24, max(2, len(volume) // 4)))
    mid, upper, lower = compute_bollinger(close)
    bb_position = None
    if upper is not None and lower is not None and not upper.dropna().empty and not lower.dropna().empty:
        denom = upper.iloc[-1] - lower.iloc[-1]
        if denom:
            bb_position = float((close.iloc[-1] - lower.iloc[-1]) / denom)
    return {
        "symbol": normalize_symbol(symbol),
        "current_price": float(close.iloc[-1]),
        "return_1h": _pct_change(klines, 1),
        "return_4h": _pct_change(klines, 4),
        "return_24h": _pct_change(klines, 24),
        "return_7d": _pct_change(klines, 24 * 7),
        "realized_vol": float(realized.dropna().iloc[-1]) if realized is not None and not realized.dropna().empty else None,
        "atr": float(atr.dropna().iloc[-1]) if atr is not None and not atr.dropna().empty else None,
        "rsi": float(rsi.dropna().iloc[-1]) if rsi is not None and not rsi.dropna().empty else None,
        "macd_hist": float(macd_hist.dropna().iloc[-1]) if macd_hist is not None and not macd_hist.dropna().empty else None,
        "bollinger_position": bb_position,
        "volume_zscore": float(volume_z.dropna().iloc[-1]) if volume_z is not None and not volume_z.dropna().empty else None,
    }, status


def merge_market_and_derivatives_snapshot(symbol: str, period: str = "1h"):
    from .crypto_derivatives import build_derivatives_snapshot

    price, price_status = get_binance_price_proxy_from_futures_klines(symbol)
    derivs, deriv_status = build_derivatives_snapshot(symbol, period=period)
    merged = {**price, **derivs}
    status = combine_results([price_status, deriv_status], provider="Crypto free-mode", source="Binance + CoinGecko snapshot")
    return merged, status
