from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_contracts import DataGap, UnifiedDataResult
from .data_router import request_price_history
from .technical_analysis import compute_atr, compute_bollinger, compute_macd, compute_rsi


def _close(frame):
    if pd is None or frame is None or getattr(frame, "empty", True):
        return pd.Series(dtype=float) if pd is not None else []
    col = "close" if "close" in frame.columns else "Close" if "Close" in frame.columns else None
    return pd.to_numeric(frame[col], errors="coerce") if col else pd.Series(dtype=float)


def _indicator_result(symbol: str, indicator: str, data: Any, base: UnifiedDataResult) -> UnifiedDataResult:
    gaps = list(base.data_gaps)
    if pd is None or data is None or getattr(data, "empty", True):
        gaps.append(DataGap(field=indicator, reason="Indicator could not be calculated from price history.", severity="high", endpoint=f"technical.{indicator}", is_blocking=True))
    return UnifiedDataResult(
        ok=bool(base.ok and not any(gap.is_blocking for gap in gaps)),
        data=data,
        provider=base.provider,
        source=base.source,
        endpoint=f"technical.{indicator}",
        native_used=True,
        openbb_used=base.openbb_used,
        fallback_used=base.fallback_used,
        is_estimated=True,
        is_proxy=base.is_proxy,
        freshness=base.freshness,
        data_gaps=gaps,
        warnings=list(base.warnings),
        errors=list(base.errors),
        caveats=["Technical indicators are research features, not timing directives."],
        metadata={**base.metadata, "symbol": symbol.upper(), "indicator": indicator},
    )


def _history(symbol: str, source_mode: str = "auto", **kwargs: Any) -> UnifiedDataResult:
    return request_price_history(symbol, source_mode="native_only" if source_mode == "auto" else source_mode, **kwargs)


def get_rsi_unified(symbol: str, *, source_mode: str = "auto", **kwargs: Any) -> UnifiedDataResult:
    base = _history(symbol, source_mode, **kwargs)
    series = compute_rsi(_close(base.data)) if pd is not None else []
    data = pd.DataFrame({"date": base.data.get("date") if hasattr(base.data, "get") else None, "symbol": symbol.upper(), "rsi": series}) if pd is not None else []
    return _indicator_result(symbol, "rsi", data, base)


def get_macd_unified(symbol: str, *, source_mode: str = "auto", **kwargs: Any) -> UnifiedDataResult:
    base = _history(symbol, source_mode, **kwargs)
    data = compute_macd(_close(base.data)) if pd is not None else []
    if pd is not None and not getattr(data, "empty", True):
        data = data.reset_index(drop=True)
        data["symbol"] = symbol.upper()
        if hasattr(base.data, "get") and "date" in base.data:
            data["date"] = base.data["date"].values[: len(data)]
    return _indicator_result(symbol, "macd", data, base)


def get_adx_unified(symbol: str, *, source_mode: str = "auto", **kwargs: Any) -> UnifiedDataResult:
    base = _history(symbol, source_mode, **kwargs)
    frame = base.data
    if pd is None or frame is None or getattr(frame, "empty", True) or not {"high", "low", "close"}.issubset(frame.columns):
        return _indicator_result(symbol, "adx", pd.DataFrame() if pd is not None else [], base)
    high = pd.to_numeric(frame["high"], errors="coerce")
    low = pd.to_numeric(frame["low"], errors="coerce")
    close = pd.to_numeric(frame["close"], errors="coerce")
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    plus_di = 100 * plus_dm.rolling(14).mean() / tr.rolling(14).mean().replace(0, pd.NA)
    minus_di = 100 * minus_dm.rolling(14).mean() / tr.rolling(14).mean().replace(0, pd.NA)
    adx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA) * 100).rolling(14).mean()
    return _indicator_result(symbol, "adx", pd.DataFrame({"date": frame.get("date"), "symbol": symbol.upper(), "adx": adx}), base)


def get_atr_unified(symbol: str, *, source_mode: str = "auto", **kwargs: Any) -> UnifiedDataResult:
    base = _history(symbol, source_mode, **kwargs)
    data = pd.DataFrame({"date": base.data.get("date") if hasattr(base.data, "get") else None, "symbol": symbol.upper(), "atr": compute_atr(base.data)}) if pd is not None else []
    return _indicator_result(symbol, "atr", data, base)


def get_bbands_unified(symbol: str, *, source_mode: str = "auto", **kwargs: Any) -> UnifiedDataResult:
    base = _history(symbol, source_mode, **kwargs)
    data = compute_bollinger(_close(base.data)) if pd is not None else []
    if pd is not None and not getattr(data, "empty", True):
        data["symbol"] = symbol.upper()
        if hasattr(base.data, "get") and "date" in base.data:
            data["date"] = base.data["date"].values[: len(data)]
    return _indicator_result(symbol, "bbands", data, base)


def get_donchian_unified(symbol: str, *, source_mode: str = "auto", window: int = 20, **kwargs: Any) -> UnifiedDataResult:
    base = _history(symbol, source_mode, **kwargs)
    frame = base.data
    if pd is None or frame is None or getattr(frame, "empty", True):
        return _indicator_result(symbol, "donchian", pd.DataFrame() if pd is not None else [], base)
    high = pd.to_numeric(frame.get("high", frame.get("close")), errors="coerce")
    low = pd.to_numeric(frame.get("low", frame.get("close")), errors="coerce")
    data = pd.DataFrame({"date": frame.get("date"), "symbol": symbol.upper(), "donchian_high": high.rolling(window).max(), "donchian_low": low.rolling(window).min()})
    return _indicator_result(symbol, "donchian", data, base)


def get_technical_factor_bundle(symbol: str, *, source_mode: str = "auto", **kwargs: Any) -> dict[str, UnifiedDataResult]:
    return {
        "rsi": get_rsi_unified(symbol, source_mode=source_mode, **kwargs),
        "macd": get_macd_unified(symbol, source_mode=source_mode, **kwargs),
        "adx": get_adx_unified(symbol, source_mode=source_mode, **kwargs),
        "atr": get_atr_unified(symbol, source_mode=source_mode, **kwargs),
        "bbands": get_bbands_unified(symbol, source_mode=source_mode, **kwargs),
        "donchian": get_donchian_unified(symbol, source_mode=source_mode, **kwargs),
    }
