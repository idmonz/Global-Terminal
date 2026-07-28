from __future__ import annotations

import math
import re
from typing import Any

from .cache import fetch_json
from .config import get_settings
from .data_status import DataResult, combine_results, failure

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


BINANCE_PROVIDER = "Binance USD-M Futures"
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]
VALID_INTERVALS = {"5m", "15m", "1h", "4h", "1d"}
VALID_PERIODS = {"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}

KLINE_COLUMNS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_buy_base_volume", "taker_buy_quote_volume"]
OI_HISTORY_COLUMNS = ["timestamp", "sum_open_interest", "sum_open_interest_value"]
FUNDING_COLUMNS = ["funding_time", "funding_rate", "symbol"]
TAKER_COLUMNS = ["timestamp", "buy_sell_ratio", "buy_volume", "sell_volume"]
RATIO_COLUMNS = ["timestamp", "long_short_ratio", "long_account", "short_account"]
TRADES_COLUMNS = ["id", "price", "qty", "quote_qty", "time", "is_buyer_maker"]


def normalize_symbol(symbol: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]", "", symbol or "").upper()
    if normalized.endswith("USD") and not normalized.endswith("USDT"):
        normalized = f"{normalized}T"
    return normalized


def validate_binance_symbol(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    if not normalized:
        raise ValueError("Symbol is required.")
    if not re.fullmatch(r"[A-Z0-9]{5,20}", normalized):
        raise ValueError(f"Unsupported Binance USD-M symbol format: {symbol}")
    if not normalized.endswith("USDT"):
        raise ValueError("Phase 4 Binance free-mode views expect USD-M USDT symbols.")
    return normalized


def _empty_frame(columns: list[str]):
    if pd is None:
        return []
    return pd.DataFrame(columns=columns)


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    except Exception:
        return None


def _to_datetime(values):
    if pd is None:
        return values
    return pd.to_datetime(values, unit="ms", utc=True, errors="coerce")


def _binance_get(path: str, *, params: dict[str, Any] | None = None, ttl_seconds: int = 120, source: str | None = None) -> tuple[Any | None, DataResult]:
    base_url = get_settings().binance_base_url.rstrip("/")
    return fetch_json(
        f"{base_url}{path}",
        params=params,
        provider=BINANCE_PROVIDER,
        source=source or path,
        ttl_seconds=ttl_seconds,
        timeout=12,
    )


def _payload_failure(source: str, message: str) -> DataResult:
    return failure(source=source, provider=BINANCE_PROVIDER, error=message, coverage="malformed response")


def _latest_row(frame, value_col: str) -> float | None:
    if frame is None or getattr(frame, "empty", True) or value_col not in frame.columns:
        return None
    values = frame[value_col].dropna()
    if values.empty:
        return None
    return _to_float(values.iloc[-1])


def get_binance_exchange_info() -> tuple[dict[str, Any], DataResult]:
    data, status = _binance_get("/fapi/v1/exchangeInfo", ttl_seconds=3600, source="Binance exchangeInfo")
    if data is None:
        return {}, status
    if not isinstance(data, dict):
        return {}, _payload_failure("Binance exchangeInfo", "Exchange info response was not a JSON object.")
    return data, status


def get_binance_klines(symbol: str, interval: str = "1h", limit: int = 200):
    normalized = validate_binance_symbol(symbol)
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Unsupported Binance kline interval: {interval}")
    payload, status = _binance_get(
        "/fapi/v1/klines",
        params={"symbol": normalized, "interval": interval, "limit": int(limit)},
        ttl_seconds=60,
        source="Binance klines",
    )
    if payload is None:
        return _empty_frame(KLINE_COLUMNS), status
    if not isinstance(payload, list):
        return _empty_frame(KLINE_COLUMNS), _payload_failure("Binance klines", "Kline response was not a list.")
    if pd is None:
        return payload, status
    rows = []
    for item in payload:
        if not isinstance(item, list) or len(item) < 11:
            continue
        rows.append(
            {
                "open_time": item[0],
                "open": item[1],
                "high": item[2],
                "low": item[3],
                "close": item[4],
                "volume": item[5],
                "close_time": item[6],
                "quote_volume": item[7],
                "trades": item[8],
                "taker_buy_base_volume": item[9],
                "taker_buy_quote_volume": item[10],
            }
        )
    frame = pd.DataFrame(rows, columns=KLINE_COLUMNS)
    if frame.empty and payload:
        return frame, _payload_failure("Binance klines", "Kline response did not match the expected schema.")
    for col in ["open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base_volume", "taker_buy_quote_volume"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["trades"] = pd.to_numeric(frame["trades"], errors="coerce").astype("Int64")
    frame["open_time"] = _to_datetime(frame["open_time"])
    frame["close_time"] = _to_datetime(frame["close_time"])
    return frame, status


def get_open_interest(symbol: str) -> tuple[dict[str, Any], DataResult]:
    normalized = validate_binance_symbol(symbol)
    payload, status = _binance_get("/fapi/v1/openInterest", params={"symbol": normalized}, ttl_seconds=30, source="Binance open interest")
    if payload is None:
        return {}, status
    if not isinstance(payload, dict):
        return {}, _payload_failure("Binance open interest", "Open interest response was not a JSON object.")
    raw_time = payload.get("time")
    return {
        "symbol": payload.get("symbol", normalized),
        "open_interest": _to_float(payload.get("openInterest")),
        "time": _to_datetime([raw_time])[0] if pd is not None and raw_time is not None else raw_time,
    }, status


def get_open_interest_history(symbol: str, period: str = "1h", limit: int = 72):
    normalized = validate_binance_symbol(symbol)
    if period not in VALID_PERIODS:
        raise ValueError(f"Unsupported Binance OI period: {period}")
    payload, status = _binance_get(
        "/futures/data/openInterestHist",
        params={"symbol": normalized, "period": period, "limit": int(limit)},
        ttl_seconds=300,
        source="Binance open interest history",
    )
    if payload is None:
        return _empty_frame(OI_HISTORY_COLUMNS), status
    if not isinstance(payload, list):
        return _empty_frame(OI_HISTORY_COLUMNS), _payload_failure("Binance open interest history", "OI history response was not a list.")
    if pd is None:
        return payload, status
    frame = pd.DataFrame(
        [{"timestamp": item.get("timestamp"), "sum_open_interest": item.get("sumOpenInterest"), "sum_open_interest_value": item.get("sumOpenInterestValue")} for item in payload if isinstance(item, dict)],
        columns=OI_HISTORY_COLUMNS,
    )
    if frame.empty and payload:
        return frame, _payload_failure("Binance open interest history", "OI history response did not match the expected schema.")
    frame["timestamp"] = _to_datetime(frame["timestamp"])
    frame["sum_open_interest"] = pd.to_numeric(frame["sum_open_interest"], errors="coerce")
    frame["sum_open_interest_value"] = pd.to_numeric(frame["sum_open_interest_value"], errors="coerce")
    return frame, status


def get_funding_rate_history(symbol: str, limit: int = 100):
    normalized = validate_binance_symbol(symbol)
    payload, status = _binance_get(
        "/fapi/v1/fundingRate",
        params={"symbol": normalized, "limit": int(limit)},
        ttl_seconds=300,
        source="Binance funding rate history",
    )
    if payload is None:
        return _empty_frame(FUNDING_COLUMNS), status
    if not isinstance(payload, list):
        return _empty_frame(FUNDING_COLUMNS), _payload_failure("Binance funding rate history", "Funding response was not a list.")
    if pd is None:
        return payload, status
    frame = pd.DataFrame(
        [{"funding_time": item.get("fundingTime"), "funding_rate": item.get("fundingRate"), "symbol": item.get("symbol", normalized)} for item in payload if isinstance(item, dict)],
        columns=FUNDING_COLUMNS,
    )
    if frame.empty and payload:
        return frame, _payload_failure("Binance funding rate history", "Funding response did not match the expected schema.")
    frame["funding_time"] = _to_datetime(frame["funding_time"])
    frame["funding_rate"] = pd.to_numeric(frame["funding_rate"], errors="coerce")
    return frame, status


def get_premium_index(symbol: str) -> tuple[dict[str, Any], DataResult]:
    normalized = validate_binance_symbol(symbol)
    payload, status = _binance_get("/fapi/v1/premiumIndex", params={"symbol": normalized}, ttl_seconds=30, source="Binance premium index")
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    if payload is None:
        return {}, status
    if not isinstance(payload, dict):
        return {}, _payload_failure("Binance premium index", "Premium index response was not a JSON object.")
    next_funding = payload.get("nextFundingTime")
    raw_time = payload.get("time")
    return {
        "symbol": payload.get("symbol", normalized),
        "mark_price": _to_float(payload.get("markPrice")),
        "index_price": _to_float(payload.get("indexPrice")),
        "estimated_settle_price": _to_float(payload.get("estimatedSettlePrice")),
        "last_funding_rate": _to_float(payload.get("lastFundingRate")),
        "next_funding_time": _to_datetime([next_funding])[0] if pd is not None and next_funding is not None else next_funding,
        "interest_rate": _to_float(payload.get("interestRate")),
        "time": _to_datetime([raw_time])[0] if pd is not None and raw_time is not None else raw_time,
    }, status


def _normalize_taker_ratio(payload: Any):
    if pd is None:
        return payload
    frame = pd.DataFrame(
        [{"timestamp": item.get("timestamp"), "buy_sell_ratio": item.get("buySellRatio"), "buy_volume": item.get("buyVol"), "sell_volume": item.get("sellVol")} for item in payload if isinstance(item, dict)],
        columns=TAKER_COLUMNS,
    )
    frame["timestamp"] = _to_datetime(frame["timestamp"])
    for col in ["buy_sell_ratio", "buy_volume", "sell_volume"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def get_taker_buy_sell_ratio(symbol: str, period: str = "1h", limit: int = 72):
    normalized = validate_binance_symbol(symbol)
    if period not in VALID_PERIODS:
        raise ValueError(f"Unsupported Binance taker period: {period}")
    payload, status = _binance_get(
        "/futures/data/takerlongshortRatio",
        params={"symbol": normalized, "period": period, "limit": int(limit)},
        ttl_seconds=300,
        source="Binance taker buy/sell ratio",
    )
    if payload is None:
        return _empty_frame(TAKER_COLUMNS), status
    if not isinstance(payload, list):
        return _empty_frame(TAKER_COLUMNS), _payload_failure("Binance taker buy/sell ratio", "Taker ratio response was not a list.")
    frame = _normalize_taker_ratio(payload)
    if getattr(frame, "empty", False) and payload:
        return frame, _payload_failure("Binance taker buy/sell ratio", "Taker ratio response did not match the expected schema.")
    return frame, status


def _normalize_long_short_ratio(payload: Any):
    if pd is None:
        return payload
    frame = pd.DataFrame(
        [{"timestamp": item.get("timestamp"), "long_short_ratio": item.get("longShortRatio"), "long_account": item.get("longAccount"), "short_account": item.get("shortAccount")} for item in payload if isinstance(item, dict)],
        columns=RATIO_COLUMNS,
    )
    frame["timestamp"] = _to_datetime(frame["timestamp"])
    for col in ["long_short_ratio", "long_account", "short_account"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def _ratio_endpoint(path: str, source: str, symbol: str, period: str, limit: int):
    normalized = validate_binance_symbol(symbol)
    if period not in VALID_PERIODS:
        raise ValueError(f"Unsupported Binance ratio period: {period}")
    payload, status = _binance_get(path, params={"symbol": normalized, "period": period, "limit": int(limit)}, ttl_seconds=300, source=source)
    if payload is None:
        return _empty_frame(RATIO_COLUMNS), status
    if not isinstance(payload, list):
        return _empty_frame(RATIO_COLUMNS), _payload_failure(source, "Long/short ratio response was not a list.")
    frame = _normalize_long_short_ratio(payload)
    if getattr(frame, "empty", False) and payload:
        return frame, _payload_failure(source, "Long/short ratio response did not match the expected schema.")
    return frame, status


def get_global_long_short_ratio(symbol: str, period: str = "1h", limit: int = 72):
    return _ratio_endpoint("/futures/data/globalLongShortAccountRatio", "Binance global long/short account ratio", symbol, period, limit)


def get_top_trader_account_ratio(symbol: str, period: str = "1h", limit: int = 72):
    return _ratio_endpoint("/futures/data/topLongShortAccountRatio", "Binance top trader account long/short ratio", symbol, period, limit)


def get_top_trader_position_ratio(symbol: str, period: str = "1h", limit: int = 72):
    return _ratio_endpoint("/futures/data/topLongShortPositionRatio", "Binance top trader position long/short ratio", symbol, period, limit)


def get_recent_trades(symbol: str, limit: int = 100):
    normalized = validate_binance_symbol(symbol)
    payload, status = _binance_get("/fapi/v1/trades", params={"symbol": normalized, "limit": min(int(limit), 1000)}, ttl_seconds=30, source="Binance recent trades")
    if payload is None:
        return _empty_frame(TRADES_COLUMNS), status
    if not isinstance(payload, list):
        return _empty_frame(TRADES_COLUMNS), _payload_failure("Binance recent trades", "Trades response was not a list.")
    if pd is None:
        return payload, status
    frame = pd.DataFrame(
        [{"id": item.get("id"), "price": item.get("price"), "qty": item.get("qty"), "quote_qty": item.get("quoteQty"), "time": item.get("time"), "is_buyer_maker": item.get("isBuyerMaker")} for item in payload if isinstance(item, dict)],
        columns=TRADES_COLUMNS,
    )
    if frame.empty and payload:
        return frame, _payload_failure("Binance recent trades", "Trades response did not match the expected schema.")
    for col in ["price", "qty", "quote_qty"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["time"] = _to_datetime(frame["time"])
    return frame, status


def build_derivatives_snapshot(symbol: str, period: str = "1h") -> tuple[dict[str, Any], DataResult]:
    normalized = validate_binance_symbol(symbol)
    open_interest, oi_status = get_open_interest(normalized)
    premium, premium_status = get_premium_index(normalized)
    funding, funding_status = get_funding_rate_history(normalized, limit=24)
    taker, taker_status = get_taker_buy_sell_ratio(normalized, period=period, limit=24)
    global_ratio, global_status = get_global_long_short_ratio(normalized, period=period, limit=24)
    top_account, top_account_status = get_top_trader_account_ratio(normalized, period=period, limit=24)
    top_position, top_position_status = get_top_trader_position_ratio(normalized, period=period, limit=24)
    mark_price = premium.get("mark_price")
    index_price = premium.get("index_price")
    premium_pct = (mark_price / index_price - 1.0) * 100.0 if mark_price and index_price else None
    items = {
        "symbol": normalized,
        "mark_price": mark_price,
        "index_price": index_price,
        "premium_pct": premium_pct,
        "open_interest": open_interest.get("open_interest"),
        "funding_rate": _latest_row(funding, "funding_rate") if _latest_row(funding, "funding_rate") is not None else premium.get("last_funding_rate"),
        "taker_buy_sell_ratio": _latest_row(taker, "buy_sell_ratio"),
        "global_long_short_ratio": _latest_row(global_ratio, "long_short_ratio"),
        "top_trader_account_ratio": _latest_row(top_account, "long_short_ratio"),
        "top_trader_position_ratio": _latest_row(top_position, "long_short_ratio"),
    }
    data_gaps = [name for name, value in items.items() if name != "symbol" and value is None]
    items["data_gaps"] = ", ".join(data_gaps) if data_gaps else "none"
    status = combine_results([oi_status, premium_status, funding_status, taker_status, global_status, top_account_status, top_position_status], provider=BINANCE_PROVIDER, source="Binance derivatives snapshot")
    return items, status


def build_derivatives_timeseries(symbol: str, period: str = "1h", limit: int = 120) -> tuple[dict[str, Any], DataResult]:
    normalized = validate_binance_symbol(symbol)
    interval = period if period in VALID_INTERVALS else "1h"
    klines, kline_status = get_binance_klines(normalized, interval=interval, limit=limit)
    oi_history, oi_status = get_open_interest_history(normalized, period=period, limit=limit)
    funding, funding_status = get_funding_rate_history(normalized, limit=min(max(limit, 1), 1000))
    taker, taker_status = get_taker_buy_sell_ratio(normalized, period=period, limit=limit)
    global_ratio, global_status = get_global_long_short_ratio(normalized, period=period, limit=limit)
    top_account, top_account_status = get_top_trader_account_ratio(normalized, period=period, limit=limit)
    top_position, top_position_status = get_top_trader_position_ratio(normalized, period=period, limit=limit)
    data = {
        "klines": klines,
        "open_interest": oi_history,
        "funding": funding,
        "taker": taker,
        "global_long_short": global_ratio,
        "top_trader_account": top_account,
        "top_trader_position": top_position,
    }
    status = combine_results([kline_status, oi_status, funding_status, taker_status, global_status, top_account_status, top_position_status], provider=BINANCE_PROVIDER, source="Binance derivatives time series")
    return data, status


def optional_provider_status(provider: str) -> DataResult:
    return failure(source=provider, provider=provider, error="Unavailable: optional paid provider/API key required.", coverage="optional paid provider", is_paid_required=True)
