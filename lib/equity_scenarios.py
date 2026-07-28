from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .compliance import contains_forbidden_language
from .data_status import error_result, ok_result
from .equity_breadth import compute_index_breadth_snapshot
from .market_data import fetch_price_history
from .technical_analysis import (
    compute_atr,
    compute_bollinger,
    compute_drawdown,
    compute_macd,
    compute_pivot_levels,
    compute_realized_vol,
    compute_relative_strength,
    compute_rsi,
    compute_sma_ema,
    compute_support_resistance,
    compute_volume_zscore,
)


def _price_history(ticker: str, period: str = "1y") -> tuple[pd.DataFrame, object]:
    return fetch_price_history(ticker, period=period)


def _latest(series: pd.Series, default=None):
    clean = series.dropna()
    if clean.empty:
        return default
    return clean.iloc[-1]


def _bucket_rsi(value) -> str:
    if pd.isna(value):
        return "Data gap"
    if value >= 70:
        return "Extended momentum"
    if value <= 30:
        return "Washed-out momentum"
    return "Neutral / mixed evidence"


def _macd_regime(macd_frame: pd.DataFrame) -> str:
    if macd_frame.empty or pd.isna(macd_frame["histogram"].iloc[-1]):
        return "Data gap"
    hist = macd_frame["histogram"].iloc[-1]
    return "Constructive technical backdrop" if hist > 0 else "Deteriorating momentum"


def compute_equity_technical_diagnostics(ticker: str, benchmark: str = "SPY", sector_proxy: str | None = None) -> tuple[dict[str, Any], object]:
    history, status = _price_history(ticker, period="1y")
    if history.empty:
        return {"ticker": ticker, "data_gaps": ["Price history unavailable."]}, error_result(source=f"yfinance:{ticker}", provider="equity_scenarios", error=status.error or "Price history unavailable.")
    close = pd.to_numeric(history["close"], errors="coerce")
    latest_close = _latest(close)
    mas = compute_sma_ema(close)
    rsi = _latest(compute_rsi(close))
    macd = compute_macd(close)
    boll = compute_bollinger(close)
    atr = compute_atr(history)
    vol_z = compute_volume_zscore(history["volume"]) if "volume" in history.columns else pd.Series(dtype=float)
    support_resistance = compute_support_resistance(history)
    pivots = compute_pivot_levels(history)
    drawdown = _latest(compute_drawdown(close), 0.0)
    realized_vol = _latest(compute_realized_vol(close), np.nan)
    benchmark_history, benchmark_status = _price_history(benchmark, period="1y")
    rel_strength = None
    if not benchmark_history.empty:
        rel_strength = _latest(compute_relative_strength(close.reset_index(drop=True), benchmark_history["close"].reset_index(drop=True)))
    sector_rs = None
    sector_status_warning = None
    if sector_proxy:
        sector_history, sector_status = _price_history(sector_proxy, period="1y")
        sector_status_warning = sector_status.error if not sector_status.ok else None
        if not sector_history.empty:
            sector_rs = _latest(compute_relative_strength(close.reset_index(drop=True), sector_history["close"].reset_index(drop=True)))
    previous = close.dropna().iloc[-2] if len(close.dropna()) > 1 else latest_close
    low_52 = close.min()
    high_52 = close.max()
    diagnostics = {
        "ticker": ticker,
        "latest_price": float(latest_close) if pd.notna(latest_close) else None,
        "price_vs_20dma": _distance(latest_close, _latest(mas.get("sma_20", pd.Series(dtype=float)))),
        "price_vs_50dma": _distance(latest_close, _latest(mas.get("sma_50", pd.Series(dtype=float)))),
        "price_vs_100dma": _distance(latest_close, _latest(mas.get("sma_100", pd.Series(dtype=float)))),
        "price_vs_200dma": _distance(latest_close, _latest(mas.get("sma_200", pd.Series(dtype=float)))),
        "rsi": float(rsi) if pd.notna(rsi) else None,
        "rsi_bucket": _bucket_rsi(rsi),
        "macd_regime": _macd_regime(macd),
        "bollinger_position": float(_latest(boll["position"], np.nan)) if not boll.empty else None,
        "atr_percentile": _percentile_rank(atr.dropna(), _latest(atr)),
        "volume_zscore": float(_latest(vol_z, np.nan)) if not vol_z.empty else None,
        "gap_vs_previous_close": _distance(latest_close, previous),
        "relative_strength_vs_benchmark": float(rel_strength) if rel_strength is not None and pd.notna(rel_strength) else None,
        "relative_strength_vs_sector": float(sector_rs) if sector_rs is not None and pd.notna(sector_rs) else None,
        "range_52w_position": _range_position(latest_close, low_52, high_52),
        "drawdown_from_52w_high": float(drawdown) if pd.notna(drawdown) else None,
        "support": support_resistance["support"],
        "resistance": support_resistance["resistance"],
        "pivot": float(_latest(pivots["pivot"], np.nan)) if not pivots.empty else None,
        "realized_volatility": float(realized_vol) if pd.notna(realized_vol) else None,
        "realized_volatility_regime": _vol_regime(realized_vol),
        "data_gaps": [gap for gap in [benchmark_status.error if not benchmark_status.ok else None, sector_status_warning] if gap],
    }
    warning = "; ".join(diagnostics["data_gaps"]) if diagnostics["data_gaps"] else status.warning
    return diagnostics, ok_result(diagnostics, source=f"yfinance:{ticker}", provider="equity_scenarios", warning=warning, coverage=f"{len(history)} price rows")


def _distance(value, reference) -> float | None:
    if value is None or reference is None or pd.isna(value) or pd.isna(reference) or reference == 0:
        return None
    return float(value / reference - 1)


def _range_position(value, low, high) -> float | None:
    if pd.isna(value) or pd.isna(low) or pd.isna(high) or high == low:
        return None
    return float((value - low) / (high - low))


def _percentile_rank(series: pd.Series, value) -> float | None:
    if series.empty or pd.isna(value):
        return None
    return float((series <= value).mean() * 100)


def _vol_regime(value) -> str:
    if pd.isna(value):
        return "Data gap"
    if value > 0.35:
        return "Elevated volatility"
    if value < 0.15:
        return "Compressed volatility"
    return "Neutral / mixed evidence"


def compute_equity_flow_proxy(ticker: str) -> tuple[dict[str, Any], object]:
    history, status = _price_history(ticker, period="6mo")
    if history.empty:
        return {"ticker": ticker, "data_gaps": ["Price and volume history unavailable."]}, error_result(source=f"yfinance:{ticker}", provider="equity_flow", error=status.error or "History unavailable.")
    close = pd.to_numeric(history["close"], errors="coerce")
    volume = pd.to_numeric(history.get("volume", pd.Series(dtype=float)), errors="coerce")
    volume_z = compute_volume_zscore(volume)
    price_change = close.pct_change()
    proxy = {
        "ticker": ticker,
        "unusual_volume_zscore": float(_latest(volume_z, np.nan)) if not volume_z.empty else None,
        "price_volume_confirmation": "Constructive technical backdrop" if _latest(price_change, 0) > 0 and _latest(volume_z, 0) > 1 else "Neutral / mixed evidence",
        "etf_sector_flow_proxy": "Use selected sector ETF relative volume as a proxy; free data does not provide confirmed fund flows.",
        "data_gaps": ["Confirmed fund-flow and short-interest feeds require optional providers."],
    }
    return proxy, ok_result(proxy, source=f"yfinance:{ticker}", provider="equity_flow", is_estimated=True, warning="Flow diagnostics are proxy estimates.")


def compute_options_chain_proxy(ticker: str) -> tuple[dict[str, Any], object]:
    try:
        import yfinance as yf

        yf_ticker = yf.Ticker(ticker)
        expiries = list(getattr(yf_ticker, "options", []) or [])
        if not expiries:
            return _missing_options(ticker, "Options expiries unavailable from yfinance.")
        expiry_rows = []
        total_put_oi = total_call_oi = total_put_vol = total_call_vol = 0.0
        largest_strikes: list[dict[str, Any]] = []
        for expiry in expiries[:4]:
            chain = yf_ticker.option_chain(expiry)
            calls = getattr(chain, "calls", pd.DataFrame()).copy()
            puts = getattr(chain, "puts", pd.DataFrame()).copy()
            call_oi = float(pd.to_numeric(calls.get("openInterest", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
            put_oi = float(pd.to_numeric(puts.get("openInterest", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
            call_vol = float(pd.to_numeric(calls.get("volume", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
            put_vol = float(pd.to_numeric(puts.get("volume", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
            total_call_oi += call_oi
            total_put_oi += put_oi
            total_call_vol += call_vol
            total_put_vol += put_vol
            expiry_rows.append({"expiry": expiry, "call_open_interest": call_oi, "put_open_interest": put_oi})
            for side, frame in [("call", calls), ("put", puts)]:
                if "openInterest" in frame.columns and "strike" in frame.columns and not frame.empty:
                    top = frame.assign(_oi=pd.to_numeric(frame["openInterest"], errors="coerce")).sort_values("_oi", ascending=False).head(3)
                    largest_strikes.extend({"expiry": expiry, "side": side, "strike": row["strike"], "open_interest": row["_oi"]} for _, row in top.iterrows())
        proxy = {
            "ticker": ticker,
            "put_call_open_interest_ratio": _safe_ratio(total_put_oi, total_call_oi),
            "put_call_volume_ratio": _safe_ratio(total_put_vol, total_call_vol),
            "largest_oi_strikes": largest_strikes[:10],
            "expiry_concentration": expiry_rows,
            "estimated_gamma_concentration_proxy": "Estimated from open-interest concentration by strike; not dealer-position data.",
            "data_gaps": ["Gamma exposure is an estimate; free yfinance chains may be delayed or incomplete."],
        }
        return proxy, ok_result(proxy, source=f"yfinance options:{ticker}", provider="equity_options", is_estimated=True, warning="Options diagnostics are delayed/proxy estimates.")
    except Exception as exc:
        return _missing_options(ticker, str(exc))


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return float(numerator / denominator)


def _missing_options(ticker: str, message: str) -> tuple[dict[str, Any], object]:
    payload = {
        "ticker": ticker,
        "put_call_open_interest_ratio": None,
        "put_call_volume_ratio": None,
        "largest_oi_strikes": [],
        "expiry_concentration": [],
        "estimated_gamma_concentration_proxy": None,
        "data_gaps": [message],
    }
    return payload, error_result(source=f"yfinance options:{ticker}", provider="equity_options", error=message, data=payload)


def compute_index_breadth_snapshot(universe: str = "sp500") -> tuple[dict, object]:
    return compute_index_breadth_snapshot_from_breadth(universe)


def compute_index_breadth_snapshot_from_breadth(universe: str = "sp500") -> tuple[dict, object]:
    return __import__("lib.equity_breadth", fromlist=["compute_index_breadth_snapshot"]).compute_index_breadth_snapshot(universe)


def compute_equity_scenario_matrix(ticker_or_index: str, horizon: str = "1w") -> tuple[pd.DataFrame, object]:
    diagnostics, tech_status = compute_equity_technical_diagnostics(ticker_or_index)
    flow, flow_status = compute_equity_flow_proxy(ticker_or_index)
    options, options_status = compute_options_chain_proxy(ticker_or_index)
    data_gaps = list(diagnostics.get("data_gaps", [])) + list(flow.get("data_gaps", [])) + list(options.get("data_gaps", []))
    base_support = diagnostics.get("support")
    base_resistance = diagnostics.get("resistance")
    rows = [
        {
            "asset_type": "equity",
            "asset": ticker_or_index,
            "horizon": horizon,
            "scenario": "Constructive continuation",
            "evidence_weight": _weight_from_diagnostics(diagnostics, positive=True),
            "evidence_summary": "Trend, relative strength, and participation evidence are reviewed for upside continuation.",
            "technical_triggers": f"Acceptance above resistance near {base_resistance}" if base_resistance else "Break above recent resistance with improving volume.",
            "breadth_confirmation": "Breadth expansion and sector participation above neutral thresholds.",
            "flow_confirmation": flow.get("price_volume_confirmation", "Neutral / mixed evidence"),
            "macro_or_sector_confirmation_needed": "Sector ETF relative strength and broad index participation.",
            "invalidation_level": f"Below support near {base_support}" if base_support else "Loss of recent support area.",
            "watch_points": "Volume z-score, relative strength, breadth regime, options concentration.",
            "catalysts": "Earnings calendar, macro data, sector news.",
            "data_gaps": "; ".join(data_gaps) if data_gaps else "None noted.",
            "confidence_caveat": "Evidence weight is not prediction certainty.",
        },
        {
            "asset_type": "equity",
            "asset": ticker_or_index,
            "horizon": horizon,
            "scenario": "Sideways consolidation",
            "evidence_weight": 50,
            "evidence_summary": "Mixed momentum and neutral breadth can support range behavior.",
            "technical_triggers": "Repeated rejection at range extremes with muted volume.",
            "breadth_confirmation": "Breadth remains balanced without broad deterioration.",
            "flow_confirmation": "Volume and options proxies remain mixed.",
            "macro_or_sector_confirmation_needed": "Stable sector backdrop and no major risk catalyst.",
            "invalidation_level": "Range break with expanding volume.",
            "watch_points": "Bollinger position, RSI bucket, volatility compression.",
            "catalysts": "Macro calendar and company-specific events.",
            "data_gaps": "; ".join(data_gaps) if data_gaps else "None noted.",
            "confidence_caveat": "Evidence weight is not prediction certainty.",
        },
        {
            "asset_type": "equity",
            "asset": ticker_or_index,
            "horizon": horizon,
            "scenario": "Downside deterioration",
            "evidence_weight": _weight_from_diagnostics(diagnostics, positive=False),
            "evidence_summary": "Weak trend, negative relative strength, or breadth deterioration can elevate downside risk.",
            "technical_triggers": f"Break below support near {base_support}" if base_support else "Break below recent support with weak breadth.",
            "breadth_confirmation": "Breadth deterioration, fewer stocks above moving averages, weak sector participation.",
            "flow_confirmation": "High volume on weakness or elevated options downside concentration proxy.",
            "macro_or_sector_confirmation_needed": "Sector ETF weakness and defensive macro regime.",
            "invalidation_level": f"Recovery above resistance near {base_resistance}" if base_resistance else "Recovery above breakdown zone.",
            "watch_points": "Advance/decline ratio, drawdown, ATR percentile.",
            "catalysts": "Earnings, rate shocks, sector/regulatory headlines.",
            "data_gaps": "; ".join(data_gaps) if data_gaps else "None noted.",
            "confidence_caveat": "Evidence weight is not prediction certainty.",
        },
        {
            "asset_type": "equity",
            "asset": ticker_or_index,
            "horizon": horizon,
            "scenario": "Event-driven volatility",
            "evidence_weight": 45 if options_status.ok else 35,
            "evidence_summary": "Options concentration, earnings, macro catalysts, or news can raise volatility risk.",
            "technical_triggers": "Gap or volatility expansion around a known catalyst.",
            "breadth_confirmation": "Index breadth reaction around event window.",
            "flow_confirmation": "Options expiry concentration and unusual volume proxy.",
            "macro_or_sector_confirmation_needed": "Calendar catalyst or sector event confirmation.",
            "invalidation_level": "Volatility fades and price returns to prior range.",
            "watch_points": "Largest open-interest strikes, volume z-score, realized volatility regime.",
            "catalysts": "Earnings, economic data, policy news.",
            "data_gaps": "; ".join(data_gaps) if data_gaps else "None noted.",
            "confidence_caveat": "Evidence weight is not prediction certainty.",
        },
    ]
    frame = pd.DataFrame(rows)
    text = " ".join(frame.astype(str).stack().tolist())
    if contains_forbidden_language(text):
        return frame, error_result(source="equity scenario engine", provider="equity_scenarios", error="Scenario text failed compliance scan.")
    warning = "; ".join(status.error for status in [tech_status, flow_status, options_status] if not status.ok) or None
    return frame, ok_result(frame, source="equity scenario engine", provider="equity_scenarios", warning=warning, is_estimated=True, coverage=f"{len(frame)} scenarios")


def _weight_from_diagnostics(diagnostics: dict[str, Any], *, positive: bool) -> int:
    score = 50
    price_vs_50 = diagnostics.get("price_vs_50dma")
    price_vs_200 = diagnostics.get("price_vs_200dma")
    rs = diagnostics.get("relative_strength_vs_benchmark")
    for value in [price_vs_50, price_vs_200, rs]:
        if value is None or pd.isna(value):
            continue
        score += 8 if value > 0 else -8
    if not positive:
        score = 100 - score
    return int(max(15, min(85, score)))


def compute_index_scenario_matrix(index_proxy: str = "SPY", horizon: str = "1w") -> tuple[pd.DataFrame, object]:
    return compute_equity_scenario_matrix(index_proxy, horizon=horizon)

