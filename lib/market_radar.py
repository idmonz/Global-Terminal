from __future__ import annotations

from statistics import mean
from typing import Any, Iterable

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def _clip(value: Any, low: float = 0.0, high: float = 100.0) -> float:
    try:
        number = float(value)
    except Exception:
        number = 0.0
    return max(low, min(high, number))


def _frame(rows: list[dict[str, Any]]):
    return pd.DataFrame(rows) if pd is not None else rows


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return value.to_dict(orient="records")
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _bucket(score: float) -> str:
    if score >= 75:
        return "Liquidity pressure"
    if score >= 60:
        return "Elevated volatility"
    if score >= 40:
        return "Mixed evidence"
    if score > 0:
        return "Constructive backdrop"
    return "Data gap"


def build_cross_asset_radar(cards: Any = None):
    rows = []
    for row in _records(cards):
        change = abs(float(row.get("change_pct") or 0.0))
        period = abs(float(row.get("period_return_pct") or row.get("return_1m_pct") or 0.0))
        score = _clip(change * 8 + period * 1.2)
        rows.append(
            {
                "component": row.get("label") or row.get("ticker") or "asset",
                "category": "cross_asset",
                "score": score,
                "label": _bucket(score),
                "method": "heuristic price move proxy",
                "source_status": row.get("data_status", "unknown"),
            }
        )
    if not rows:
        rows.append({"component": "cross asset", "category": "cross_asset", "score": 0.0, "label": "Data gap", "method": "heuristic price move proxy", "source_status": "missing"})
    return _frame(rows)


def build_equity_breadth_radar(equity: dict[str, Any] | None = None):
    equity = equity or {}
    above_50 = equity.get("above_50dma_pct") or equity.get("sp500_above_50dma_pct")
    above_200 = equity.get("above_200dma_pct") or equity.get("sp500_above_200dma_pct")
    breadth = equity.get("breadth") or equity.get("advance_decline")
    deterioration = 50.0
    if above_50 is not None:
        deterioration += (50.0 - float(above_50)) * 0.7
    if above_200 is not None:
        deterioration += (50.0 - float(above_200)) * 0.5
    if isinstance(breadth, (int, float)):
        deterioration += (0.5 - float(breadth)) * 20.0
    score = _clip(deterioration)
    return _frame(
        [
            {
                "component": "equity breadth",
                "category": "equity",
                "score": score,
                "label": "Deteriorating breadth" if score >= 60 else _bucket(score),
                "method": "heuristic breadth proxy",
                "source_status": equity.get("data_status", "proxy estimate"),
            }
        ]
    )


def build_crypto_derivatives_radar(snapshot: dict[str, Any] | None = None, pressure_map: Any = None):
    snapshot = snapshot or {}
    funding = abs(float(snapshot.get("funding_rate") or 0.0)) * 10000
    taker = abs(float(snapshot.get("taker_buy_sell_ratio") or snapshot.get("taker_ratio") or 1.0) - 1.0) * 35
    long_short = abs(float(snapshot.get("global_long_short_ratio") or 1.0) - 1.0) * 35
    pressure = 0.0
    if pressure_map is not None and hasattr(pressure_map, "empty") and not pressure_map.empty and "pressure_score" in pressure_map.columns:
        pressure = float(pressure_map["pressure_score"].fillna(0).mean())
    score = _clip(funding + taker + long_short + pressure * 0.25)
    return _frame(
        [
            {
                "component": "crypto derivatives",
                "category": "crypto",
                "score": score,
                "label": "Crowding risk" if score >= 55 else _bucket(score),
                "method": "heuristic derivatives stress proxy",
                "source_status": snapshot.get("source_status", "proxy estimate"),
            }
        ]
    )


def build_energy_risk_radar(energy: dict[str, Any] | None = None, news_risk: dict[str, Any] | None = None):
    energy = energy or {}
    news_risk = news_risk or {}
    score = float(news_risk.get("score") or 0.0)
    chokepoint_text = str(energy.get("chokepoint_risk_proxy") or "").lower()
    if "elevated" in chokepoint_text:
        score += 25
    elif "watch" in chokepoint_text or "proxy" in chokepoint_text:
        score += 15
    if "unavailable" in str(energy.get("inventory_status") or "").lower():
        score += 10
    score = _clip(score)
    return _frame(
        [
            {
                "component": "energy/geopolitical",
                "category": "energy",
                "score": score,
                "label": "Elevated volatility" if score >= 60 else _bucket(score),
                "method": "heuristic energy and news proxy",
                "source_status": "proxy estimate",
            }
        ]
    )


def build_volatility_radar(risk: dict[str, Any] | None = None, cards: Any = None):
    risk = risk or {}
    vix = risk.get("vix")
    if vix is None:
        for row in _records(cards):
            if str(row.get("label", "")).upper() == "VIX":
                vix = row.get("price")
                break
    score = _clip((float(vix or 0.0) - 12.0) * 4.0) if vix is not None else 0.0
    return _frame(
        [
            {
                "component": "volatility",
                "category": "risk",
                "score": score,
                "label": "Elevated volatility" if score >= 55 else _bucket(score),
                "method": "VIX regime proxy",
                "source_status": risk.get("source_status", "real/delayed if available"),
            }
        ]
    )


def _iter_scores(radars: Iterable[Any]) -> list[float]:
    scores: list[float] = []
    for radar in radars:
        if radar is None:
            continue
        if hasattr(radar, "columns") and "score" in radar.columns:
            scores.extend(float(value) for value in radar["score"].dropna().tolist())
        elif isinstance(radar, list):
            scores.extend(float(item.get("score", 0)) for item in radar if isinstance(item, dict))
    return [_clip(score) for score in scores]


def build_market_composite_score(*radars: Any) -> dict[str, Any]:
    scores = _iter_scores(radars)
    score = round(mean(scores), 1) if scores else 0.0
    return {
        "score": score,
        "label": _bucket(score),
        "components": len(scores),
        "method": "Heuristic composite across available market radar components.",
        "is_estimated": True,
    }
