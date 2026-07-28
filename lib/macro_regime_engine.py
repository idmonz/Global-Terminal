from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


REGIME_LABELS = [
    "easing",
    "tightening",
    "disinflation",
    "inflation pressure",
    "growth slowing",
    "growth improving",
    "dollar strength",
    "dollar weakness",
    "volatility elevated",
    "mixed evidence",
    "data gap",
]


def _latest_change(result: Any) -> float | None:
    data = getattr(result, "data", None)
    if pd is None or data is None or getattr(data, "empty", True):
        return None
    frame = data.copy()
    numeric = [col for col in frame.columns if col in {"value", "rate", "close", "latest_price"}]
    if not numeric:
        numeric = list(frame.select_dtypes("number").columns)
    if not numeric:
        return None
    series = pd.to_numeric(frame[numeric[0]], errors="coerce").dropna()
    if len(series) < 2:
        return None
    return float(series.iloc[-1] - series.iloc[max(0, len(series) - 4)])


def compute_macro_regime_score(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    results = payload.get("results", {})
    changes = {name: _latest_change(result) for name, result in results.items()}
    gaps = [name for name, value in changes.items() if value is None]
    inflation_pressure = sum(1 for name in ["cpi", "pce"] if changes.get(name) is not None and changes[name] > 0)
    growth_improving = changes.get("gdp") is not None and changes["gdp"] > 0
    labor_tight = changes.get("unemployment") is not None and changes["unemployment"] < 0
    rates_up = changes.get("treasury_curve") is not None and changes["treasury_curve"] > 0
    score = 50.0
    score += inflation_pressure * 10
    score += 8 if rates_up else -5 if changes.get("treasury_curve") is not None else 0
    score += 8 if growth_improving else -8 if changes.get("gdp") is not None else 0
    score += 6 if labor_tight else -6 if changes.get("unemployment") is not None else 0
    score -= min(25, len(gaps) * 4)
    return {
        "score": round(max(0.0, min(100.0, score)), 1),
        "changes": changes,
        "data_gaps": gaps,
        "source_confidence": payload.get("source_confidence", 0),
    }


def classify_macro_regime(score_payload: dict[str, Any] | None = None) -> str:
    score_payload = score_payload or {}
    if len(score_payload.get("data_gaps", [])) >= 5:
        return "data gap"
    changes = score_payload.get("changes", {})
    if (changes.get("cpi") or 0) < 0 and (changes.get("pce") or 0) < 0:
        return "disinflation"
    if (changes.get("cpi") or 0) > 0 or (changes.get("pce") or 0) > 0:
        return "inflation pressure"
    if (changes.get("treasury_curve") or 0) > 0:
        return "tightening"
    if (changes.get("treasury_curve") or 0) < 0:
        return "easing"
    if (changes.get("gdp") or 0) > 0:
        return "growth improving"
    if (changes.get("gdp") or 0) < 0:
        return "growth slowing"
    return "mixed evidence"


def build_macro_regime_evidence(payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    score_payload = compute_macro_regime_score(payload)
    rows = []
    for name, change in score_payload["changes"].items():
        rows.append(
            {
                "indicator": name,
                "latest_change": change,
                "evidence_state": "data gap" if change is None else "rising" if change > 0 else "falling" if change < 0 else "flat",
                "source_confidence": score_payload["source_confidence"],
            }
        )
    return rows


def build_macro_regime_cards(payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    score_payload = compute_macro_regime_score(payload)
    label = classify_macro_regime(score_payload)
    return [
        {
            "label": "Macro Regime",
            "value": label,
            "score": score_payload["score"],
            "source_confidence": score_payload["source_confidence"],
            "data_gaps": score_payload["data_gaps"],
            "caveat": "Regime labels are heuristic research context and not financial advice.",
        }
    ]


def build_macro_regime_ai_context(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    score_payload = compute_macro_regime_score(payload)
    return {
        "macro_regime": classify_macro_regime(score_payload),
        "score": score_payload["score"],
        "evidence": build_macro_regime_evidence(payload),
        "data_gaps": score_payload["data_gaps"],
        "allowed_language": REGIME_LABELS,
        "caveat": "Use neutral regime language only; no trade directives.",
    }
