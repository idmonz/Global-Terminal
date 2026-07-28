from __future__ import annotations

from itertools import combinations
from statistics import mean
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def run_alpha_combination_search(leaderboard: Any, *, max_size: int = 3, top_n: int = 10):
    frame = leaderboard.copy() if hasattr(leaderboard, "copy") else pd.DataFrame(leaderboard or [])
    if frame.empty:
        return pd.DataFrame() if pd is not None else []
    name_col = "candidate" if "candidate" in frame.columns else "name"
    score_col = "risk_adjusted_score" if "risk_adjusted_score" in frame.columns else "score"
    rows = frame.to_dict(orient="records")
    candidates = []
    for size in range(2, min(max_size, len(rows)) + 1):
        for bundle in combinations(rows, size):
            score = mean(float(item.get(score_col, 0) or 0) for item in bundle)
            coverage = mean(float(item.get("factor_coverage_pct", 50) or 50) for item in bundle)
            candidates.append(
                {
                    "name": " + ".join(str(item.get(name_col, "Strategy")) for item in bundle),
                    "size": size,
                    "composite_score": round(score * 0.75 + coverage * 0.25, 2),
                    "factor_coverage_pct": round(coverage, 2),
                    "caveat": "Alpha combinations are research candidates and require validation.",
                }
            )
    result = sorted(candidates, key=lambda item: item["composite_score"], reverse=True)[:top_n]
    return pd.DataFrame(result) if pd is not None else result


def build_alpha_combination_cards(combinations_frame: Any) -> list[dict[str, Any]]:
    records = combinations_frame.to_dict(orient="records") if hasattr(combinations_frame, "to_dict") else list(combinations_frame or [])
    return [
        {"title": row.get("name", "Alpha combination"), "summary": f"Composite score {row.get('composite_score', 'N/A')} with factor coverage {row.get('factor_coverage_pct', 'N/A')}.", "severity": "watch", "tags": ["alpha combination", "research candidate"]}
        for row in records[:6]
    ]
