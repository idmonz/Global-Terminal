from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd


SIGNAL_CAVEAT = "Research signal only; it is not financial advice, not a prediction, and not a directive."
VALID_DIRECTIONS = {"constructive", "neutral", "deteriorating", "defensive", "crowded", "data_gap"}
DEFAULT_ALPHA_FAMILIES = ["momentum", "trend", "low_volatility", "value", "quality", "carry", "macro_rotation", "news_impact"]


def _prices_frame(prices: Any) -> pd.DataFrame:
    if prices is None:
        return pd.DataFrame()
    frame = prices.copy() if isinstance(prices, pd.DataFrame) else pd.DataFrame(prices)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.set_index("date")
    return frame.apply(pd.to_numeric, errors="coerce").dropna(how="all")


def _score(value: Any, center: float = 0.0, scale: float = 1.0) -> float:
    try:
        number = float(value)
    except Exception:
        return 50.0
    return float(max(0.0, min(100.0, 50.0 + (number - center) / scale * 50.0)))


def _direction(score: float, *, crowded: bool = False, defensive: bool = False, gap: bool = False) -> str:
    if gap:
        return "data_gap"
    if crowded:
        return "crowded"
    if defensive:
        return "defensive"
    if score >= 60:
        return "constructive"
    if score <= 40:
        return "deteriorating"
    return "neutral"


def _signal(name: str, family: str, asset: str, score: float, direction_label: str, evidence: dict[str, Any] | str, data_gaps: list[str] | None = None) -> dict[str, Any]:
    return {
        "signal_name": name,
        "family": family,
        "asset": asset,
        "score": round(float(max(0.0, min(100.0, score))), 1),
        "direction_label": direction_label if direction_label in VALID_DIRECTIONS else "neutral",
        "evidence": evidence,
        "data_gaps": data_gaps or [],
        "caveat": SIGNAL_CAVEAT,
    }


def _returns(prices: pd.DataFrame, periods: int) -> pd.Series:
    if prices.empty or len(prices) <= periods:
        return pd.Series(dtype=float)
    return prices.iloc[-1] / prices.shift(periods).iloc[-1] - 1.0


def compute_momentum_signal(prices: Any, *, skip_last_month: bool = True) -> list[dict[str, Any]]:
    frame = _prices_frame(prices)
    if frame.empty:
        return [_signal("Momentum data gap", "momentum", "portfolio", 0, "data_gap", {}, ["No price history supplied."])]
    base = frame.shift(21) if skip_last_month and len(frame) > 43 else frame
    rows = []
    for asset in frame.columns:
        evidence = {
            "return_1m": float(_returns(base[[asset]], 21).get(asset, np.nan)) if len(base) > 21 else np.nan,
            "return_3m": float(_returns(base[[asset]], 63).get(asset, np.nan)) if len(base) > 63 else np.nan,
            "return_6m": float(_returns(base[[asset]], 126).get(asset, np.nan)) if len(base) > 126 else np.nan,
            "return_12m": float(_returns(base[[asset]], 252).get(asset, np.nan)) if len(base) > 252 else np.nan,
            "skip_last_month": skip_last_month,
        }
        values = [value for value in evidence.values() if isinstance(value, float) and pd.notna(value)]
        score = _score(np.mean(values), center=0.0, scale=0.20) if values else 0
        rows.append(_signal("Multi-horizon momentum", "momentum", asset, score, _direction(score, gap=not values), evidence, [] if values else ["Insufficient lookback."]))
    return rows


def compute_trend_signal(prices: Any) -> list[dict[str, Any]]:
    frame = _prices_frame(prices)
    rows = []
    for asset in frame.columns:
        series = frame[asset].dropna()
        if len(series) < 60:
            rows.append(_signal("Trend data gap", "trend", asset, 0, "data_gap", {}, ["Need at least 60 observations."]))
            continue
        dma50 = float(series.rolling(50).mean().iloc[-1])
        dma200 = float(series.rolling(min(200, len(series))).mean().iloc[-1])
        price = float(series.iloc[-1])
        donchian = float(series.iloc[-1] / series.rolling(min(55, len(series))).max().iloc[-1] - 1.0)
        vol_breakout = float(series.pct_change().iloc[-21:].std() / max(series.pct_change().std(), 1e-9))
        points = [price > dma50, price > dma200, dma50 > dma200, donchian > -0.02, vol_breakout < 1.8]
        score = sum(points) / len(points) * 100
        rows.append(_signal("Trend following proxy", "trend", asset, score, _direction(score), {"price": price, "dma50": dma50, "dma200": dma200, "donchian_proxy": donchian, "volatility_breakout_proxy": vol_breakout}))
    return rows or [_signal("Trend data gap", "trend", "portfolio", 0, "data_gap", {}, ["No price history supplied."])]


def compute_mean_reversion_signal(prices: Any) -> list[dict[str, Any]]:
    frame = _prices_frame(prices)
    rows = []
    for asset in frame.columns:
        series = frame[asset].dropna()
        if len(series) < 30:
            rows.append(_signal("Mean reversion data gap", "mean_reversion", asset, 0, "data_gap", {}, ["Need at least 30 observations."]))
            continue
        returns = series.pct_change()
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
        zscore = float((series.iloc[-1] - series.rolling(20).mean().iloc[-1]) / max(series.rolling(20).std().iloc[-1], 1e-9))
        short_reversal = float(-returns.iloc[-5:].sum())
        raw = (50 - abs(float(rsi.iloc[-1]) - 50)) + max(0.0, short_reversal * 250) + max(0.0, -zscore * 15)
        score = max(0.0, min(100.0, raw))
        rows.append(_signal("Mean reversion proxy", "mean_reversion", asset, score, _direction(score), {"rsi": float(rsi.iloc[-1]), "bollinger_z_score": zscore, "short_term_reversal": short_reversal}))
    return rows or [_signal("Mean reversion data gap", "mean_reversion", "portfolio", 0, "data_gap", {}, ["No price history supplied."])]


def compute_low_volatility_signal(prices: Any) -> list[dict[str, Any]]:
    frame = _prices_frame(prices)
    returns = frame.pct_change()
    if returns.empty:
        return [_signal("Low volatility data gap", "low_volatility", "portfolio", 0, "data_gap", {}, ["No price history supplied."])]
    vol = returns.rolling(min(63, len(returns))).std().iloc[-1]
    drawdown = frame / frame.cummax() - 1
    downside = returns.mask(returns > 0).rolling(min(63, len(returns))).std().iloc[-1]
    rows = []
    for asset in frame.columns:
        evidence = {"realized_volatility": float(vol.get(asset, np.nan)), "drawdown": float(drawdown[asset].iloc[-1]), "downside_volatility": float(downside.get(asset, np.nan))}
        ranks = vol.rank(pct=True, ascending=False)
        score = float(ranks.get(asset, 0.5) * 100)
        rows.append(_signal("Low volatility rank", "low_volatility", asset, score, _direction(score, defensive=score >= 60), evidence))
    return rows


def compute_value_signal(fundamentals: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = []
    for asset, data in (fundamentals or {}).items():
        pe = data.get("pe") or data.get("trailing_pe")
        ps = data.get("ps") or data.get("price_to_sales")
        pb = data.get("pb") or data.get("price_to_book")
        ev_ebitda = data.get("ev_ebitda")
        fcf_yield = data.get("fcf_yield")
        components = []
        if pe:
            components.append(100 - min(100, float(pe) * 3))
        if ps:
            components.append(100 - min(100, float(ps) * 10))
        if pb:
            components.append(100 - min(100, float(pb) * 12))
        if ev_ebitda:
            components.append(100 - min(100, float(ev_ebitda) * 4))
        if fcf_yield is not None:
            components.append(_score(float(fcf_yield), center=0.03, scale=0.08))
        gaps = [] if components else ["Fundamental valuation fields unavailable."]
        score = float(np.mean(components)) if components else 0.0
        rows.append(_signal("Value proxy", "value", asset, score, _direction(score, gap=not components), {"pe": pe, "ps": ps, "pb": pb, "ev_ebitda": ev_ebitda, "fcf_yield": fcf_yield}, gaps))
    return rows or [_signal("Value data gap", "value", "portfolio", 0, "data_gap", {}, ["No valuation data supplied."])]


def compute_quality_signal(fundamentals: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = []
    for asset, data in (fundamentals or {}).items():
        components = []
        for key, center, scale in [("roe", 0.12, 0.18), ("roa", 0.05, 0.10), ("margin", 0.15, 0.25), ("fcf_margin", 0.08, 0.18)]:
            if data.get(key) is not None:
                components.append(_score(data[key], center=center, scale=scale))
        if data.get("debt_to_equity") is not None:
            components.append(100 - min(100, float(data["debt_to_equity"]) * 25))
        score = float(np.mean(components)) if components else 0.0
        rows.append(_signal("Quality proxy", "quality", asset, score, _direction(score, gap=not components), data, [] if components else ["Quality fields unavailable."]))
    return rows or [_signal("Quality data gap", "quality", "portfolio", 0, "data_gap", {}, ["No quality data supplied."])]


def compute_carry_signal(carry_data: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = []
    for asset, data in (carry_data or {}).items():
        value = data.get("bond_carry") or data.get("commodity_carry") or data.get("crypto_funding") or data.get("dividend_yield")
        score = _score(value, center=0.02, scale=0.08) if value is not None else 0
        rows.append(_signal("Carry proxy", "carry", asset, score, _direction(score, gap=value is None, crowded=(data.get("crypto_funding") or 0) > 0.03), data, [] if value is not None else ["Carry fields unavailable."]))
    return rows or [_signal("Carry data gap", "carry", "portfolio", 0, "data_gap", {}, ["No carry data supplied."])]


def compute_macro_rotation_signal(regime: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    regime = regime or {}
    stress = sum(float(regime.get(key, 0) or 0) for key in ["rates_regime", "dxy_regime", "oil_regime", "vix_regime"]) / 4.0 if regime else 0
    breadth = float(regime.get("breadth_regime", 50) or 50)
    score = max(0.0, min(100.0, breadth - stress * 10 + 20))
    return [_signal("Macro rotation proxy", "macro_rotation", regime.get("asset", "portfolio"), score, _direction(score, defensive=score < 45), regime, [] if regime else ["Macro regime inputs unavailable."])]


def compute_crypto_derivatives_signal(derivatives: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = []
    for asset, data in (derivatives or {}).items():
        funding = float(data.get("funding_percentile", data.get("funding_rate", 0)) or 0)
        oi_change = float(data.get("oi_change", 0) or 0)
        taker = float(data.get("taker_imbalance", 0) or 0)
        ratio = float(data.get("long_short_ratio", 1) or 1)
        pressure = float(data.get("liquidation_pressure", 0) or 0)
        crowding = abs(funding - 50) + abs(ratio - 1) * 20 + pressure
        score = max(0.0, min(100.0, 100 - crowding + oi_change * 20 + taker * 10))
        rows.append(_signal("Crypto derivatives stress-aware proxy", "crypto_derivatives", asset, score, _direction(score, crowded=crowding > 60), data, []))
    return rows or [_signal("Crypto derivatives data gap", "crypto_derivatives", "crypto", 0, "data_gap", {}, ["Derivatives data unavailable."])]


def compute_news_impact_signal(events: Any = None) -> list[dict[str, Any]]:
    if isinstance(events, pd.DataFrame):
        frame = events.copy()
    else:
        frame = pd.DataFrame(events or [])
    if frame.empty:
        return [_signal("News impact data gap", "news_impact", "portfolio", 0, "data_gap", {}, ["No event rows supplied."])]
    severity_map = {"critical": 95, "high": 78, "elevated": 55, "medium": 45, "watch": 30, "low": 15}
    rows = []
    for asset in sorted({asset for values in frame.get("related_tickers", []) for asset in (values if isinstance(values, list) else [values]) if asset}):
        related = frame[frame.get("related_tickers", pd.Series(dtype=object)).apply(lambda value: asset in value if isinstance(value, list) else value == asset)]
        score = min(100.0, float(related.get("severity", pd.Series(["watch"])).map(severity_map).fillna(30).mean() if not related.empty else 0))
        rows.append(_signal("News-aware impact proxy", "news_impact", asset, score, _direction(score, defensive=score >= 70), {"event_count": int(len(related)), "source_count": int(related.get("source", pd.Series(dtype=object)).nunique())}, []))
    return rows or [_signal("News impact data gap", "news_impact", "portfolio", 0, "data_gap", {}, ["No related assets found."])]


def compute_defensive_regime_signal(context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    stress = float(context.get("risk_score", context.get("vix", 0)) or 0)
    score = min(100.0, stress if stress <= 100 else stress / 2)
    return [_signal("Defensive regime proxy", "defensive_regime", context.get("asset", "portfolio"), score, _direction(score, defensive=score >= 55), context, [] if context else ["Defensive regime inputs unavailable."])]


def compute_multi_signal_score(signals: list[dict[str, Any]], *, weights: dict[str, float] | None = None) -> pd.DataFrame:
    if not signals:
        return pd.DataFrame(columns=["asset", "signal_count", "multi_signal_score", "direction_label", "data_gaps", "caveat"])
    weights = weights or {}
    frame = pd.DataFrame(signals)
    rows = []
    for asset, group in frame.groupby("asset"):
        weighted = []
        for _, row in group.iterrows():
            weighted.append(float(row["score"]) * float(weights.get(row["family"], 1.0)))
        denominator = sum(float(weights.get(row["family"], 1.0)) for _, row in group.iterrows()) or 1.0
        score = sum(weighted) / denominator
        gaps = [gap for gaps in group["data_gaps"] for gap in (gaps if isinstance(gaps, list) else [gaps]) if gap]
        rows.append({"asset": asset, "signal_count": int(len(group)), "multi_signal_score": round(score, 1), "direction_label": _direction(score, gap=bool(gaps) and score == 0), "data_gaps": gaps, "caveat": SIGNAL_CAVEAT})
    return pd.DataFrame(rows).sort_values("multi_signal_score", ascending=False)


def generate_alpha_combinations(families: list[str] | None = None, *, max_size: int = 3) -> list[dict[str, Any]]:
    families = families or DEFAULT_ALPHA_FAMILIES
    output: list[dict[str, Any]] = []
    for size in range(1, min(max_size, len(families)) + 1):
        for combo in combinations(families, size):
            output.append(
                {
                    "name": " + ".join(part.replace("_", " ").title() for part in combo),
                    "families": list(combo),
                    "description": "Alpha combination for neutral research comparison.",
                    "caveat": "Signal combination is a research candidate.",
                }
            )
    return output


def build_alpha_factor_backend_context(symbols: list[str], *, source_mode: str = "auto") -> dict[str, Any]:
    from .openbb_factor_backend import build_factor_backend_table

    payload = build_factor_backend_table(symbols, source_mode=source_mode)
    return {
        "factor_table": payload["table"],
        "payloads": payload["payloads"],
        "families": DEFAULT_ALPHA_FAMILIES + ["options_aware", "defensive_regime"],
        "caveat": "Factor backend context is research input only.",
    }
