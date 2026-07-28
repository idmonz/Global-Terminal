from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from .heatmap_layout_engine import build_heatmap_layout


def _records(rows: Any) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if hasattr(rows, "to_dict"):
        return rows.to_dict(orient="records")
    return [dict(item) for item in rows or []]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def compute_volatility_zscore(value: Any, history: list[float] | None = None) -> float:
    value_num = _number(value)
    series = [float(item) for item in history or [] if item is not None]
    if len(series) < 2:
        baseline = 20.0
        spread = 10.0
    else:
        baseline = mean(series)
        spread = pstdev(series) or 1.0
    return round((value_num - baseline) / spread, 3)


def compute_drawdown_state(drawdown: Any) -> str:
    value = _number(drawdown)
    if value <= -20:
        return "severe drawdown"
    if value <= -10:
        return "elevated drawdown"
    if value <= -5:
        return "watch"
    return "contained"


def classify_global_volatility_state(zscore: float, drawdown: Any = 0) -> str:
    if zscore >= 2 or compute_drawdown_state(drawdown) == "severe drawdown":
        return "severe"
    if zscore >= 1 or compute_drawdown_state(drawdown) == "elevated drawdown":
        return "elevated"
    if zscore <= -0.75:
        return "calm"
    return "watch"


def build_volatility_ranking(rows: Any) -> list[dict[str, Any]]:
    output = []
    for row in _records(rows):
        vol = _number(row.get("realized_vol") or row.get("realized_volatility_pct") or row.get("volatility"))
        drawdown = _number(row.get("drawdown_52w") or row.get("drawdown_pct"))
        zscore = compute_volatility_zscore(vol, row.get("vol_history"))
        state = classify_global_volatility_state(zscore, drawdown)
        risk_score = max(0.0, min(100.0, 45 + zscore * 18 + abs(min(drawdown, 0)) * 1.2))
        output.append({**row, "symbol": row.get("symbol") or row.get("ticker") or row.get("label"), "volatility_zscore": zscore, "drawdown_state": compute_drawdown_state(drawdown), "volatility_state": state, "risk_score": round(risk_score, 2), "source": row.get("source", "market rows"), "freshness": row.get("freshness", "estimated")})
    return sorted(output, key=lambda item: item["risk_score"], reverse=True)


def build_volatility_cards(rows: Any) -> list[dict[str, Any]]:
    ranking = build_volatility_ranking(rows)
    severe = [row for row in ranking if row["volatility_state"] == "severe"]
    elevated = [row for row in ranking if row["volatility_state"] == "elevated"]
    return [
        {"title": "Global Volatility State", "summary": f"{len(severe)} severe and {len(elevated)} elevated assets in supplied rows.", "severity": "high" if severe else "medium" if elevated else "watch", "tags": ["volatility"], "freshness": "estimated"},
        {"title": "Highest Volatility", "summary": ", ".join(str(row.get("symbol")) for row in ranking[:5]) or "No rows supplied.", "severity": "watch", "tags": ["ranking"], "freshness": "estimated"},
    ]


def build_volatility_heatmap(rows: Any) -> dict[str, Any]:
    ranking = build_volatility_ranking(rows)
    return build_heatmap_layout(ranking, title="Global Volatility Monitor Heatmap", size_mode="equal", color_mode="risk_score", group_mode="asset_class")


def build_global_volatility_monitor(rows: Any) -> dict[str, Any]:
    ranking = build_volatility_ranking(rows)
    severe_count = sum(1 for row in ranking if row["volatility_state"] == "severe")
    elevated_count = sum(1 for row in ranking if row["volatility_state"] == "elevated")
    state = "severe" if severe_count else "elevated" if elevated_count else "watch"
    return {
        "state": state,
        "ranking": ranking,
        "cards": build_volatility_cards(ranking),
        "heatmap": build_volatility_heatmap(ranking),
        "methodology": "Volatility state uses realized volatility z-score and drawdown severity for research context.",
    }


def build_global_volatility_payload(rows: Any = None) -> dict[str, Any]:
    """Compatibility wrapper for Goal 10B/11 canonical guard checks."""
    return build_global_volatility_monitor(rows or [])
