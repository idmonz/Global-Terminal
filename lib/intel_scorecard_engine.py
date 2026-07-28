from __future__ import annotations

from statistics import mean
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def _score(value: Any, *, neutral: float = 50.0, scale: float = 1.0, invert: bool = False) -> float:
    try:
        number = float(value)
    except Exception:
        return neutral
    score = neutral + number * scale
    if invert:
        score = 100 - score
    return round(max(0.0, min(100.0, score)), 1)


def _label(score: float) -> str:
    if score >= 67:
        return "constructive"
    if score <= 33:
        return "deteriorating"
    return "mixed"


def score_price_trend(change_pct: Any = None, momentum_pct: Any = None) -> dict[str, Any]:
    score = mean([_score(change_pct, scale=2.0), _score(momentum_pct, scale=1.2)])
    return {"factor": "price_trend", "score": round(score, 1), "label": _label(score), "source": "price history"}


def score_valuation(pe: Any = None, ev_sales: Any = None) -> dict[str, Any]:
    pe_score = _score(pe, neutral=65, scale=-1.2)
    ev_score = _score(ev_sales, neutral=60, scale=-3.0)
    score = mean([pe_score, ev_score])
    return {"factor": "valuation", "score": round(score, 1), "label": _label(score), "source": "fundamentals/proxy"}


def score_quality(gross_margin: Any = None, roe: Any = None) -> dict[str, Any]:
    score = mean([_score(gross_margin, scale=0.6), _score(roe, scale=1.0)])
    return {"factor": "quality", "score": round(score, 1), "label": _label(score), "source": "fundamentals/proxy"}


def score_growth(revenue_growth: Any = None, earnings_growth: Any = None) -> dict[str, Any]:
    score = mean([_score(revenue_growth, scale=1.0), _score(earnings_growth, scale=0.8)])
    return {"factor": "growth", "score": round(score, 1), "label": _label(score), "source": "fundamentals/proxy"}


def score_balance_sheet(debt_to_equity: Any = None, current_ratio: Any = None) -> dict[str, Any]:
    score = mean([_score(debt_to_equity, neutral=65, scale=-8.0), _score(current_ratio, neutral=40, scale=15.0)])
    return {"factor": "balance_sheet", "score": round(score, 1), "label": _label(score), "source": "fundamentals/proxy"}


def score_market_risk(beta: Any = None, drawdown_pct: Any = None) -> dict[str, Any]:
    score = mean([_score(beta, neutral=60, scale=-12.0), _score(drawdown_pct, neutral=50, scale=1.0)])
    return {"factor": "market_risk", "score": round(score, 1), "label": _label(score), "source": "price/risk proxy"}


def build_security_scorecard(symbol: str, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    metrics = metrics or {}
    rows = [
        score_price_trend(metrics.get("change_pct"), metrics.get("momentum_pct")),
        score_valuation(metrics.get("pe"), metrics.get("ev_sales")),
        score_quality(metrics.get("gross_margin"), metrics.get("roe")),
        score_growth(metrics.get("revenue_growth"), metrics.get("earnings_growth")),
        score_balance_sheet(metrics.get("debt_to_equity"), metrics.get("current_ratio")),
        score_market_risk(metrics.get("beta"), metrics.get("drawdown_pct")),
    ]
    aggregate = round(mean(row["score"] for row in rows), 1)
    data_quality = "insufficient data" if not metrics else "proxy" if any(value is None for value in metrics.values()) else "available"
    return {
        "symbol": str(symbol or "").upper(),
        "score": aggregate,
        "label": "insufficient data" if not metrics else _label(aggregate),
        "factors": rows,
        "data_quality": data_quality,
        "caveat": "Security scorecards are neutral research summaries, not advice or predictions.",
    }


def build_scorecard_table(scorecard: dict[str, Any]):
    rows = list(scorecard.get("factors", []))
    return pd.DataFrame(rows) if pd is not None else rows


def summarize_scorecard(scorecard: dict[str, Any]) -> str:
    return f"{scorecard.get('symbol', 'Asset')} scorecard is {scorecard.get('label', 'mixed')} with data quality marked {scorecard.get('data_quality', 'unknown')}."
