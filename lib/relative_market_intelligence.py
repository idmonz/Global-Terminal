from __future__ import annotations

from statistics import mean
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


def compute_relative_strength_score(row: dict[str, Any], *, benchmark_return: float = 0.0) -> float:
    daily = _number(row.get("daily_return") or row.get("change_pct") or row.get("return_1d_pct"))
    monthly = _number(row.get("monthly_return") or row.get("return_1m_pct"))
    vol = abs(_number(row.get("realized_vol") or row.get("realized_volatility_pct"), 20.0))
    raw = 50 + (daily - benchmark_return) * 4 + monthly * 1.5 - max(0.0, vol - 25.0) * 0.35
    return round(max(0.0, min(100.0, raw)), 2)


def classify_rmi_state(score: float) -> str:
    if score >= 70:
        return "leader"
    if score >= 55:
        return "resilient"
    if score <= 30:
        return "stressed laggard"
    if score <= 45:
        return "laggard"
    return "mixed"


def build_rmi_table(rows: Any, *, benchmark_symbol: str = "SPY") -> list[dict[str, Any]]:
    records = _records(rows)
    benchmark_return = 0.0
    for row in records:
        if str(row.get("ticker") or row.get("symbol")).upper() == benchmark_symbol.upper():
            benchmark_return = _number(row.get("daily_return") or row.get("change_pct") or row.get("return_1d_pct"))
            break
    output = []
    for row in records:
        score = compute_relative_strength_score(row, benchmark_return=benchmark_return)
        output.append(
            {
                **row,
                "symbol": row.get("symbol") or row.get("ticker") or row.get("label"),
                "relative_strength_score": score,
                "relative_state": classify_rmi_state(score),
                "benchmark": benchmark_symbol,
                "source": row.get("source", "market rows"),
                "freshness": row.get("freshness", row.get("data_quality", "estimated")),
            }
        )
    return sorted(output, key=lambda item: item["relative_strength_score"], reverse=True)


def build_rmi_cards(rows: Any, *, benchmark_symbol: str = "SPY") -> list[dict[str, Any]]:
    table = build_rmi_table(rows, benchmark_symbol=benchmark_symbol)
    top = table[:3]
    laggards = list(reversed(table[-3:])) if len(table) >= 3 else []
    avg = round(mean([row["relative_strength_score"] for row in table]), 2) if table else 0.0
    return [
        {"title": "RMI Average", "summary": f"Relative market score averages {avg}.", "severity": "watch", "tags": ["RMI", benchmark_symbol], "freshness": "estimated"},
        {"title": "Relative Leaders", "summary": ", ".join(str(row.get("symbol")) for row in top) or "No rows supplied.", "severity": "low", "tags": ["leaders"], "freshness": "estimated"},
        {"title": "Relative Laggards", "summary": ", ".join(str(row.get("symbol")) for row in laggards) or "No rows supplied.", "severity": "medium" if laggards else "watch", "tags": ["laggards"], "freshness": "estimated"},
    ]


def build_rmi_heatmap(rows: Any, *, benchmark_symbol: str = "SPY") -> dict[str, Any]:
    table = build_rmi_table(rows, benchmark_symbol=benchmark_symbol)
    return build_heatmap_layout(table, title="Relative Market Intelligence Heatmap", size_mode="equal", color_mode="relative_strength", group_mode="asset_class")


def build_relative_market_intelligence(rows: Any, *, benchmark_symbol: str = "SPY") -> dict[str, Any]:
    table = build_rmi_table(rows, benchmark_symbol=benchmark_symbol)
    return {
        "benchmark": benchmark_symbol,
        "table": table,
        "cards": build_rmi_cards(table, benchmark_symbol=benchmark_symbol),
        "heatmap": build_rmi_heatmap(table, benchmark_symbol=benchmark_symbol),
        "methodology": "Relative score blends recent return versus benchmark with a volatility penalty for research context.",
    }
