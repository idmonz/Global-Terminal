from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


SEVERITY_SCORE = {"low": 15, "watch": 30, "elevated": 55, "high": 78, "critical": 95}
FRESHNESS_PENALTY = {"fresh": 0, "estimated": 5, "stale": 12, "missing": 20, "error": 25, "unknown": 10}


def _clip(value: Any, low: float = 0.0, high: float = 100.0) -> float:
    try:
        number = float(value)
    except Exception:
        number = 0.0
    return max(low, min(high, number))


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return value.to_dict(orient="records")
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return []


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _frame(rows: list[dict[str, Any]]):
    return pd.DataFrame(rows) if pd is not None else rows


def _recency_score(timestamp: Any) -> float:
    if timestamp is None or pd is None:
        return 35.0
    parsed = pd.to_datetime(timestamp, utc=True, errors="coerce")
    if pd.isna(parsed):
        return 35.0
    age_hours = max(0.0, (datetime.now(timezone.utc) - parsed.to_pydatetime()).total_seconds() / 3600.0)
    if age_hours <= 6:
        return 100.0
    if age_hours <= 24:
        return 80.0
    if age_hours <= 72:
        return 55.0
    return 30.0


def compute_event_severity(event: dict[str, Any]) -> dict[str, Any]:
    base = SEVERITY_SCORE.get(str(event.get("severity") or "watch").lower(), 30)
    confidence = _clip(float(event.get("confidence") or 0.45) * 100)
    source_bonus = min(12, len(set(_list(event.get("sources") or event.get("source")))) * 3)
    asset_bonus = min(12, len(set(_list(event.get("related_assets") or event.get("related_tickers")))) * 2)
    freshness_penalty = FRESHNESS_PENALTY.get(str(event.get("freshness_status") or event.get("freshness") or "unknown").lower(), 10)
    score = _clip(base * 0.55 + confidence * 0.25 + source_bonus + asset_bonus - freshness_penalty)
    return {
        "severity": "critical" if score >= 90 else "high" if score >= 75 else "elevated" if score >= 55 else "watch" if score >= 25 else "low",
        "score": round(score, 1),
        "drivers": ["headline severity", "confidence", "source count", "related assets", "freshness penalty"],
        "caveat": "Heuristic event severity; not an official intelligence score.",
    }


def compute_signal_convergence(
    *,
    news_severity: Any = None,
    source_count: int = 0,
    market_move: Any = 0,
    volatility_move: Any = 0,
    crypto_derivatives_stress: Any = 0,
    oil_chokepoint_risk: Any = 0,
    data_freshness: str = "unknown",
    related_assets: int = 0,
    recency: Any = None,
) -> dict[str, Any]:
    severity_component = SEVERITY_SCORE.get(str(news_severity or "watch").lower(), _clip(news_severity))
    source_component = min(100, max(0, int(source_count)) * 18)
    market_component = min(100, abs(float(market_move or 0)) * 12)
    vol_component = min(100, abs(float(volatility_move or 0)) * 8)
    crypto_component = _clip(crypto_derivatives_stress)
    oil_component = _clip(oil_chokepoint_risk)
    asset_component = min(100, max(0, int(related_assets)) * 10)
    freshness_component = max(0, 100 - FRESHNESS_PENALTY.get(str(data_freshness or "unknown").lower(), 10) * 3)
    recency_component = _recency_score(recency)
    score = mean(
        [
            severity_component,
            source_component,
            market_component,
            vol_component,
            crypto_component,
            oil_component,
            asset_component,
            freshness_component,
            recency_component,
        ]
    )
    return {
        "score": round(_clip(score), 1),
        "drivers": {
            "news_severity": round(_clip(severity_component), 1),
            "source_count": round(_clip(source_component), 1),
            "market_move": round(_clip(market_component), 1),
            "volatility_move": round(_clip(vol_component), 1),
            "crypto_derivatives_stress": round(_clip(crypto_component), 1),
            "oil_chokepoint_risk": round(_clip(oil_component), 1),
            "related_assets": round(_clip(asset_component), 1),
            "freshness": round(_clip(freshness_component), 1),
            "recency": round(_clip(recency_component), 1),
        },
        "freshness": data_freshness,
        "caveat": "Signal convergence is heuristic and correlation/proxy based.",
    }


def compute_asset_hotspot_score(asset: str, events: Any = None, market_context: dict[str, Any] | None = None) -> dict[str, Any]:
    market_context = market_context or {}
    related = []
    for event in _records(events):
        tickers = [str(item).upper() for item in _list(event.get("related_tickers") or event.get("related_assets"))]
        if str(asset).upper() in tickers:
            related.append(event)
    source_count = len({row.get("source") for row in related if row.get("source")})
    max_severity = max([SEVERITY_SCORE.get(str(row.get("severity") or "watch").lower(), 30) for row in related] or [0])
    context = compute_signal_convergence(
        news_severity=max_severity,
        source_count=source_count,
        market_move=market_context.get("latest_return_pct") or market_context.get("return_1d_pct") or 0,
        volatility_move=market_context.get("volatility_change") or 0,
        data_freshness=market_context.get("freshness") or "unknown",
        related_assets=len(related),
    )
    return {
        "hotspot": asset,
        "domain": "asset",
        "score": context["score"],
        "drivers": context["drivers"],
        "related_assets": [asset],
        "source_count": source_count,
        "freshness": market_context.get("freshness") or "unknown",
        "caveat": "Asset hotspot score is a proxy reaction screen, not a directive.",
    }


def compute_region_hotspot_score(region: str, events: Any = None) -> dict[str, Any]:
    related = [event for event in _records(events) if str(event.get("region") or "").lower() == str(region or "").lower()]
    source_count = len({row.get("source") for row in related if row.get("source")})
    severity = max([SEVERITY_SCORE.get(str(row.get("severity") or "watch").lower(), 30) for row in related] or [0])
    context = compute_signal_convergence(news_severity=severity, source_count=source_count, related_assets=sum(len(_list(row.get("related_tickers"))) for row in related), data_freshness="estimated")
    return {
        "hotspot": region or "Global",
        "domain": "region",
        "score": context["score"],
        "drivers": context["drivers"],
        "related_assets": sorted({asset for row in related for asset in _list(row.get("related_tickers"))})[:8],
        "source_count": source_count,
        "freshness": "estimated",
        "caveat": "Regional hotspot score is heuristic, based on available event rows.",
    }


def compute_chokepoint_hotspot_score(chokepoint: dict[str, Any], events: Any = None) -> dict[str, Any]:
    name = str(chokepoint.get("title") or chokepoint.get("name") or "")
    tokens = [token for token in name.lower().replace("strait of ", "").replace("canal", "").split() if len(token) > 2]
    related = []
    for event in _records(events):
        text = f"{event.get('title', '')} {event.get('summary', '')}".lower()
        if any(token in text for token in tokens):
            related.append(event)
    context = compute_signal_convergence(
        news_severity=max([SEVERITY_SCORE.get(str(row.get("severity") or "watch").lower(), 30) for row in related] or [35]),
        source_count=len({row.get("source") for row in related if row.get("source")}),
        oil_chokepoint_risk=60 if related else 35,
        data_freshness="estimated",
        related_assets=len(_list(chokepoint.get("related_tickers"))),
    )
    return {
        "hotspot": name or "Chokepoint",
        "domain": "chokepoint",
        "score": context["score"],
        "drivers": context["drivers"],
        "related_assets": _list(chokepoint.get("related_tickers")),
        "source_count": len(related),
        "freshness": "estimated",
        "caveat": "Static chokepoint score; no live AIS or vessel tracking is claimed.",
    }


def build_hotspot_leaderboard(events: Any = None, market_context: dict[str, Any] | None = None):
    rows: list[dict[str, Any]] = []
    event_rows = _records(events)
    assets = sorted({asset for event in event_rows for asset in _list(event.get("related_tickers") or event.get("related_assets"))})
    regions = sorted({str(event.get("region") or "Global") for event in event_rows})
    for asset in assets[:20]:
        rows.append(compute_asset_hotspot_score(asset, event_rows, (market_context or {}).get(asset, {})))
    for region in regions[:12]:
        rows.append(compute_region_hotspot_score(region, event_rows))
    rows = sorted(rows, key=lambda item: item["score"], reverse=True)
    return _frame(rows)


def build_intelligence_watchpoints(events: Any = None, limit: int = 8) -> list[dict[str, Any]]:
    watchpoints = []
    for event in sorted(_records(events), key=lambda row: SEVERITY_SCORE.get(str(row.get("severity") or "watch").lower(), 0), reverse=True)[:limit]:
        scored = compute_event_severity(event)
        watchpoints.append(
            {
                "title": event.get("title") or "Event watch-point",
                "domain": event.get("domain") or "unknown",
                "score": scored["score"],
                "severity": scored["severity"],
                "drivers": scored["drivers"],
                "related_assets": _list(event.get("related_tickers") or event.get("related_assets")),
                "source_count": 1 if event.get("source") else 0,
                "freshness": event.get("freshness_status") or event.get("freshness") or "unknown",
                "caveat": "Watch-points are neutral scenario evidence, not instructions.",
            }
        )
    return watchpoints
