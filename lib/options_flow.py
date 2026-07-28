from __future__ import annotations

from datetime import datetime, timezone
from math import exp, log, sqrt
from typing import Any

from .data_status import failure, success

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

try:
    from scipy.stats import norm
except Exception:  # pragma: no cover
    norm = None


GAMMA_CAVEAT = "Estimated gamma exposure proxy, not dealer-confirmed GEX."


def _ticker(ticker: str):
    if yf is None:
        return None
    try:
        return yf.Ticker(ticker)
    except Exception:
        return None


def get_options_expirations(ticker: str):
    if yf is None:
        return [], failure(source=f"{ticker} options expirations", provider="yfinance options", error="yfinance is not installed")
    obj = _ticker(ticker)
    if obj is None:
        return [], failure(source=f"{ticker} options expirations", provider="yfinance options", error="Ticker object unavailable")
    try:
        expirations = list(getattr(obj, "options", []) or [])
        return expirations, success(expirations, source=f"{ticker} options expirations", provider="yfinance options", coverage=f"{len(expirations)} expiries")
    except Exception as exc:
        return [], failure(source=f"{ticker} options expirations", provider="yfinance options", error=str(exc), coverage="missing")


def get_options_chain(ticker: str, expiry: str | None = None):
    if pd is None or yf is None:
        return {"calls": pd.DataFrame() if pd is not None else [], "puts": pd.DataFrame() if pd is not None else []}, failure(source=f"{ticker} options chain", provider="yfinance options", error="pandas or yfinance is not installed")
    obj = _ticker(ticker)
    if obj is None:
        return {"calls": pd.DataFrame(), "puts": pd.DataFrame()}, failure(source=f"{ticker} options chain", provider="yfinance options", error="Ticker object unavailable")
    try:
        expirations = list(getattr(obj, "options", []) or [])
        expiry = expiry or (expirations[0] if expirations else None)
        if not expiry:
            return {"calls": pd.DataFrame(), "puts": pd.DataFrame(), "expiry": None}, failure(source=f"{ticker} options chain", provider="yfinance options", error="No option expirations available", coverage="missing")
        chain = obj.option_chain(expiry)
        info = getattr(obj, "fast_info", {}) or {}
        underlying = info.get("last_price") or info.get("lastPrice") or info.get("regularMarketPrice")
        data = {"calls": chain.calls.copy(), "puts": chain.puts.copy(), "expiry": expiry, "underlying_price": underlying}
        return data, success(data, source=f"{ticker} options chain {expiry}", provider="yfinance options", coverage="calls and puts")
    except Exception as exc:
        return {"calls": pd.DataFrame(), "puts": pd.DataFrame(), "expiry": expiry}, failure(source=f"{ticker} options chain", provider="yfinance options", error=str(exc), coverage="missing")


def _sum_column(frame, column: str) -> float:
    if frame is None or getattr(frame, "empty", True) or column not in frame.columns:
        return 0.0
    return float(frame[column].fillna(0).sum())


def compute_put_call_oi_ratio(calls, puts) -> float | None:
    calls_oi = _sum_column(calls, "openInterest")
    puts_oi = _sum_column(puts, "openInterest")
    return puts_oi / calls_oi if calls_oi else None


def compute_put_call_volume_ratio(calls, puts) -> float | None:
    calls_volume = _sum_column(calls, "volume")
    puts_volume = _sum_column(puts, "volume")
    return puts_volume / calls_volume if calls_volume else None


def compute_max_pain_proxy(calls, puts) -> dict[str, Any]:
    if pd is None or calls is None or puts is None or (getattr(calls, "empty", True) and getattr(puts, "empty", True)):
        return {"max_pain_strike": None, "caveat": "Option chain unavailable."}
    strikes = sorted(set(calls.get("strike", pd.Series(dtype=float)).dropna().tolist()) | set(puts.get("strike", pd.Series(dtype=float)).dropna().tolist()))
    losses = []
    for strike in strikes:
        call_oi = calls["openInterest"].fillna(0) if not getattr(calls, "empty", True) and "openInterest" in calls.columns else 0
        put_oi = puts["openInterest"].fillna(0) if not getattr(puts, "empty", True) and "openInterest" in puts.columns else 0
        call_loss = (((strike - calls["strike"]).clip(lower=0)) * call_oi).sum() if not getattr(calls, "empty", True) and "strike" in calls.columns else 0
        put_loss = (((puts["strike"] - strike).clip(lower=0)) * put_oi).sum() if not getattr(puts, "empty", True) and "strike" in puts.columns else 0
        losses.append({"strike": strike, "estimated_payout": float(call_loss + put_loss)})
    frame = pd.DataFrame(losses)
    if frame.empty:
        return {"max_pain_strike": None, "caveat": "Option chain unavailable."}
    row = frame.sort_values("estimated_payout").iloc[0]
    return {"max_pain_strike": float(row["strike"]), "estimated_payout": float(row["estimated_payout"]), "caveat": "Max pain is a simplified open-interest proxy."}


def _bs_gamma(spot: float, strike: float, iv: float, days: float, rate: float = 0.045) -> float | None:
    if norm is None or spot <= 0 or strike <= 0 or iv <= 0 or days <= 0:
        return None
    t = days / 365.0
    d1 = (log(spot / strike) + (rate + 0.5 * iv * iv) * t) / (iv * sqrt(t))
    return float(norm.pdf(d1) / (spot * iv * sqrt(t)))


def compute_gamma_exposure_proxy(calls, puts, underlying_price: float | None, expiry: str | None = None):
    if pd is None:
        return []
    rows = []
    spot = float(underlying_price) if underlying_price else None
    days = 30.0
    if expiry:
        try:
            expiry_dt = datetime.fromisoformat(expiry).replace(tzinfo=timezone.utc)
            days = max(1.0, (expiry_dt - datetime.now(timezone.utc)).total_seconds() / 86400)
        except Exception:
            days = 30.0
    for side, frame, sign in [("call", calls, 1), ("put", puts, -1)]:
        if frame is None or getattr(frame, "empty", True):
            continue
        for _, row in frame.iterrows():
            strike = row.get("strike")
            if strike is None:
                continue
            oi = row.get("openInterest") or 0
            iv = row.get("impliedVolatility") or None
            gamma = _bs_gamma(spot, float(strike), float(iv), days) if spot and strike and iv else None
            if gamma is None:
                proximity = max(0.0, 1.0 - abs(float(strike) / spot - 1.0)) if spot and strike else 0.0
                proxy = float(oi) * proximity * sign
                method = "OI-weighted strike proximity proxy"
            else:
                proxy = float(oi) * 100 * spot * spot * gamma * 0.01 * sign
                method = "Black-Scholes gamma approximation"
            rows.append({"strike": float(strike), "side": side, "gamma_proxy": proxy, "open_interest": float(oi), "method": method, "caveat": GAMMA_CAVEAT})
    return pd.DataFrame(rows)


def compute_largest_oi_strikes(calls, puts, top_n: int = 10):
    if pd is None:
        return []
    rows = []
    for side, frame in [("call", calls), ("put", puts)]:
        if frame is None or getattr(frame, "empty", True) or "openInterest" not in frame.columns:
            continue
        subset = frame[["strike", "openInterest", "volume"] if "volume" in frame.columns else ["strike", "openInterest"]].copy()
        subset["side"] = side
        rows.append(subset)
    if not rows:
        return pd.DataFrame(columns=["strike", "openInterest", "side"])
    return pd.concat(rows, ignore_index=True).sort_values("openInterest", ascending=False).head(top_n)


def compute_expiry_concentration(chains: list[dict[str, Any]]):
    if pd is None:
        return []
    rows = []
    for chain in chains:
        calls = chain.get("calls")
        puts = chain.get("puts")
        rows.append(
            {
                "expiry": chain.get("expiry"),
                "call_open_interest": _sum_column(calls, "openInterest"),
                "put_open_interest": _sum_column(puts, "openInterest"),
                "total_open_interest": _sum_column(calls, "openInterest") + _sum_column(puts, "openInterest"),
            }
        )
    return pd.DataFrame(rows)


def build_options_dashboard(ticker: str, expiry: str | None = None):
    chain, status = get_options_chain(ticker, expiry)
    calls = chain.get("calls")
    puts = chain.get("puts")
    underlying = chain.get("underlying_price")
    gamma = compute_gamma_exposure_proxy(calls, puts, underlying, chain.get("expiry"))
    dashboard = {
        "ticker": ticker.upper(),
        "expiry": chain.get("expiry"),
        "underlying_price": underlying,
        "put_call_oi_ratio": compute_put_call_oi_ratio(calls, puts),
        "put_call_volume_ratio": compute_put_call_volume_ratio(calls, puts),
        "max_pain_proxy": compute_max_pain_proxy(calls, puts),
        "largest_oi_strikes": compute_largest_oi_strikes(calls, puts),
        "gamma_proxy": gamma,
        "expiry_concentration": compute_expiry_concentration([chain]),
        "caveat": GAMMA_CAVEAT,
        "data_gaps": [] if status.ok else [status.error or "options chain unavailable"],
    }
    return dashboard, status


def build_options_visual_payload(dashboard: dict[str, Any]) -> dict[str, Any]:
    dashboard = dashboard or {}
    gamma = dashboard.get("gamma_proxy")
    largest = dashboard.get("largest_oi_strikes")
    expiry = dashboard.get("expiry_concentration")
    summary_cards = [
        {"label": "Underlying", "value": dashboard.get("underlying_price"), "status": "source-derived" if dashboard.get("underlying_price") is not None else "data gap"},
        {"label": "Put/Call OI Ratio", "value": dashboard.get("put_call_oi_ratio"), "status": "proxy"},
        {"label": "Put/Call Volume Ratio", "value": dashboard.get("put_call_volume_ratio"), "status": "proxy"},
        {"label": "Max Pain Proxy", "value": (dashboard.get("max_pain_proxy") or {}).get("max_pain_strike"), "status": "proxy"},
    ]
    return {
        "ticker": dashboard.get("ticker"),
        "expiry": dashboard.get("expiry"),
        "summary_cards": summary_cards,
        "gamma_by_strike": gamma if gamma is not None else (pd.DataFrame() if pd is not None else []),
        "open_interest_by_strike": largest if largest is not None else (pd.DataFrame() if pd is not None else []),
        "expiry_concentration": expiry if expiry is not None else (pd.DataFrame() if pd is not None else []),
        "caveat_badges": [GAMMA_CAVEAT, "Proxy estimate", "Dealer-confirmed exposure unavailable"],
        "method": "options visual payload builder",
    }
