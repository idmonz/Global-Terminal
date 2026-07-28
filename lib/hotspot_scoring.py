from __future__ import annotations

from typing import Any, Iterable

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def _clip(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except Exception:
        return 0.0


def _label(score: float) -> str:
    if score >= 75:
        return "High hotspot pressure"
    if score >= 55:
        return "Elevated hotspot pressure"
    if score >= 30:
        return "Watch-point"
    return "Low current signal"


def compute_region_hotspot_score(region: str | dict[str, Any], news_count: int = 0, high_severity_count: int = 0, market_stress: float = 0.0, source_penalty: float = 0.0) -> dict[str, Any]:
    payload = dict(region) if isinstance(region, dict) else {"region": region}
    news_count = int(payload.get("headline_count", payload.get("news_count", news_count)) or 0)
    high_severity_count = int(payload.get("high_count", payload.get("high_severity_count", high_severity_count)) or 0)
    market_stress = float(payload.get("market_stress", payload.get("score", market_stress)) or 0.0)
    source_penalty = float(payload.get("source_penalty", source_penalty) or 0.0)
    score = _clip(news_count * 4 + high_severity_count * 18 + market_stress * 0.45 + source_penalty)
    return {
        "name": payload.get("region") or payload.get("name") or "Global",
        "type": "region",
        "score": score,
        "label": _label(score),
        "method": "heuristic regional hotspot score",
        "is_estimated": True,
    }


def compute_asset_hotspot_score(asset: str | dict[str, Any], return_abs_pct: float = 0.0, volatility_score: float = 0.0, news_severity_score: float = 0.0, data_gap_penalty: float = 0.0) -> dict[str, Any]:
    payload = dict(asset) if isinstance(asset, dict) else {"asset": asset}
    return_abs_pct = abs(float(payload.get("return_abs_pct", payload.get("change_abs_pct", return_abs_pct)) or 0.0))
    volatility_score = float(payload.get("volatility_score", payload.get("realized_volatility_pct", volatility_score)) or 0.0)
    news_severity_score = float(payload.get("news_severity_score", news_severity_score) or 0.0)
    data_gap_penalty = float(payload.get("data_gap_penalty", data_gap_penalty) or 0.0)
    score = _clip(return_abs_pct * 5 + volatility_score * 0.6 + news_severity_score * 0.55 + data_gap_penalty)
    return {
        "name": payload.get("asset") or payload.get("ticker") or payload.get("label") or "asset",
        "type": "asset",
        "score": score,
        "label": _label(score),
        "method": "heuristic asset hotspot score",
        "is_estimated": True,
    }


def compute_chokepoint_hotspot_score(chokepoint: str | dict[str, Any], related_headlines: int = 0, risk_proxy: str = "watch", source_penalty: float = 0.0) -> dict[str, Any]:
    payload = dict(chokepoint) if isinstance(chokepoint, dict) else {"name": chokepoint}
    related_headlines = int(payload.get("related_headlines", payload.get("headline_count", related_headlines)) or 0)
    risk_proxy = str(payload.get("risk_proxy", risk_proxy) or "watch").lower()
    base = 55 if "elevated" in risk_proxy else 35 if "watch" in risk_proxy else 20
    score = _clip(base + related_headlines * 10 + float(payload.get("source_penalty", source_penalty) or 0.0))
    return {
        "name": payload.get("name") or "chokepoint",
        "type": "chokepoint",
        "score": score,
        "label": _label(score),
        "method": "heuristic chokepoint hotspot score; no live AIS claim",
        "is_estimated": True,
    }


def build_hotspot_leaderboard(
    regions: Iterable[Any] | None = None,
    assets: Iterable[Any] | None = None,
    chokepoints: Iterable[Any] | None = None,
):
    rows = []
    rows.extend(compute_region_hotspot_score(item) for item in regions or [])
    rows.extend(compute_asset_hotspot_score(item) for item in assets or [])
    rows.extend(compute_chokepoint_hotspot_score(item) for item in chokepoints or [])
    if pd is None:
        return sorted(rows, key=lambda item: item["score"], reverse=True)
    columns = ["name", "type", "score", "label", "method", "is_estimated"]
    return pd.DataFrame(rows, columns=columns).sort_values("score", ascending=False) if rows else pd.DataFrame(columns=columns)
