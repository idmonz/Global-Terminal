from __future__ import annotations

from statistics import mean
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
        return "Liquidity pressure"
    if score >= 60:
        return "Elevated volatility"
    if score >= 40:
        return "Mixed evidence"
    if score > 0:
        return "Constructive backdrop"
    return "Data gap"


def _frame(rows: list[dict[str, Any]]):
    return pd.DataFrame(rows) if pd is not None else rows


def normalize_signal(
    name: str,
    value: Any,
    *,
    category: str = "market",
    weight: float = 1.0,
    confidence: float = 0.5,
    source_status: str = "unknown",
    note: str = "",
) -> dict[str, Any]:
    score = _clip(value)
    return {
        "name": name,
        "category": category,
        "score": score,
        "weight": max(0.0, float(weight)),
        "confidence": max(0.0, min(1.0, float(confidence))),
        "label": _label(score),
        "source_status": source_status,
        "note": note,
        "method": "heuristic signal normalization",
    }


def _weighted_fusion(signals: Iterable[dict[str, Any]], category: str) -> dict[str, Any]:
    rows = [signal for signal in signals if signal]
    if not rows:
        return normalize_signal(f"{category} fusion", 0, category=category, source_status="missing", note="No signals supplied.")
    total_weight = sum(float(row.get("weight", 1.0)) for row in rows) or 1.0
    score = sum(float(row.get("score", 0.0)) * float(row.get("weight", 1.0)) for row in rows) / total_weight
    confidence = mean(float(row.get("confidence", 0.5)) for row in rows)
    return normalize_signal(
        f"{category} fusion",
        score,
        category=category,
        confidence=confidence,
        source_status="; ".join(sorted({str(row.get("source_status", "unknown")) for row in rows})),
        note=f"{len(rows)} signal(s) fused.",
    )


def fuse_market_signals(signals: Iterable[dict[str, Any]] | None = None, cards: Any = None) -> dict[str, Any]:
    rows = list(signals or [])
    if cards is not None and hasattr(cards, "to_dict"):
        for row in cards.to_dict(orient="records"):
            score = abs(float(row.get("change_pct") or 0.0)) * 10 + abs(float(row.get("period_return_pct") or 0.0))
            rows.append(normalize_signal(str(row.get("label") or row.get("ticker")), score, category="market", source_status=row.get("data_status", "unknown")))
    return _weighted_fusion(rows, "market")


def fuse_news_signals(news_dashboard: dict[str, Any] | None = None) -> dict[str, Any]:
    news_dashboard = news_dashboard or {}
    impact = news_dashboard.get("impact_matrix")
    score = 0.0
    count = 0
    if hasattr(impact, "empty") and not impact.empty:
        score = float((impact.get("critical_count", 0) * 25 + impact.get("high_count", 0) * 18 + impact.get("medium_count", 0) * 10).sum())
        count = int(impact.get("total_count", 0).sum())
    return normalize_signal("news severity fusion", min(100, score), category="news", confidence=0.55 if count else 0.2, source_status="heuristic public news", note=f"{count} classified items.")


def fuse_energy_signals(energy: dict[str, Any] | None = None, news_signal: dict[str, Any] | None = None) -> dict[str, Any]:
    energy = energy or {}
    base = 20.0 if energy else 0.0
    if "unavailable" in str(energy.get("inventory_status") or "").lower():
        base += 15
    if "chokepoint" in str(energy.get("chokepoint_risk_proxy") or "").lower():
        base += 20
    if news_signal:
        base += float(news_signal.get("score", 0.0)) * 0.35
    return normalize_signal("energy fusion", base, category="energy", confidence=0.45, source_status="proxy estimate", note="No live vessel flow is assumed.")


def fuse_crypto_signals(snapshot: dict[str, Any] | None = None, radar: Any = None) -> dict[str, Any]:
    snapshot = snapshot or {}
    score = abs(float(snapshot.get("funding_rate") or 0.0)) * 10000
    score += abs(float(snapshot.get("global_long_short_ratio") or 1.0) - 1.0) * 35
    if hasattr(radar, "empty") and not radar.empty and "score" in radar.columns:
        score += float(radar["score"].mean()) * 0.5
    return normalize_signal("crypto fusion", score, category="crypto", confidence=0.5, source_status="public derivatives if available", note="Crowding proxy.")


def build_signal_convergence_table(signals: Iterable[dict[str, Any]] | None = None):
    rows = [signal for signal in signals or [] if signal]
    if pd is None:
        return rows
    columns = ["category", "signal_count", "average_score", "max_score", "average_confidence", "dominant_label", "source_status", "method"]
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    grouped_rows = []
    for category, group in frame.groupby("category"):
        avg = float(group["score"].mean())
        grouped_rows.append(
            {
                "category": category,
                "signal_count": int(len(group)),
                "average_score": round(avg, 1),
                "max_score": round(float(group["score"].max()), 1),
                "average_confidence": round(float(group["confidence"].mean()), 2),
                "dominant_label": _label(avg),
                "source_status": "; ".join(sorted({str(value) for value in group["source_status"].dropna().tolist()})),
                "method": "heuristic signal convergence",
            }
        )
    return pd.DataFrame(grouped_rows, columns=columns).sort_values("average_score", ascending=False)


def compute_signal_convergence(**kwargs: Any) -> dict[str, Any]:
    from .intelligence_scoring import compute_signal_convergence as _compute_signal_convergence

    return _compute_signal_convergence(**kwargs)
