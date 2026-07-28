from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_router import request_options_chain


def get_options_factor_data(symbol: str, *, source_mode: str = "auto") -> dict[str, Any]:
    result = request_options_chain(symbol, source_mode=source_mode, allow_proxy=True)
    return {"symbol": symbol.upper(), "result": result, "data": result.data, "data_gaps": result.data_gaps, "source_confidence": result.metadata.get("source_confidence", 0)}


def _sum_by_type(data: Any, field: str) -> tuple[float, float]:
    if pd is None or data is None or getattr(data, "empty", True) or field not in data.columns:
        return 0.0, 0.0
    frame = data.copy()
    type_col = "call_put" if "call_put" in frame.columns else "option_type" if "option_type" in frame.columns else None
    if type_col is None:
        return 0.0, 0.0
    values = pd.to_numeric(frame[field], errors="coerce").fillna(0)
    calls = float(values[frame[type_col].astype(str).str.lower().str.startswith("c")].sum())
    puts = float(values[frame[type_col].astype(str).str.lower().str.startswith("p")].sum())
    return calls, puts


def compute_put_call_oi_ratio(data: Any) -> float | None:
    calls, puts = _sum_by_type(data, "open_interest")
    return round(puts / calls, 4) if calls else None


def compute_put_call_volume_ratio(data: Any) -> float | None:
    calls, puts = _sum_by_type(data, "volume")
    return round(puts / calls, 4) if calls else None


def compute_iv_proxy_signal(data: Any) -> dict[str, Any]:
    if pd is None or data is None or getattr(data, "empty", True) or "iv" not in data.columns:
        return {"factor": "iv_proxy", "score": 0.0, "data_gap": "IV unavailable.", "is_proxy": True}
    iv = pd.to_numeric(data["iv"], errors="coerce").dropna()
    score = float(iv.rank(pct=True).iloc[-1] * 100) if not iv.empty else 0.0
    return {"factor": "iv_proxy", "score": round(score, 1), "data_gap": None, "is_proxy": True}


def compute_gamma_proxy_signal(data: Any) -> dict[str, Any]:
    if pd is None or data is None or getattr(data, "empty", True):
        return {"factor": "gamma_proxy", "score": 0.0, "data_gap": "Options chain unavailable.", "is_proxy": True, "caveat": "Gamma is proxy-labeled."}
    if "gamma" in data.columns:
        gamma = pd.to_numeric(data["gamma"], errors="coerce").abs().sum()
        score = min(100.0, float(gamma) * 100)
    else:
        oi = pd.to_numeric(data.get("open_interest", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
        score = min(100.0, float(oi) / 10000.0)
    return {"factor": "gamma_proxy", "score": round(score, 1), "data_gap": None, "is_proxy": True, "caveat": "Gamma exposure is a proxy unless official provider gamma is present."}


def build_options_factor_scores(symbol: str, *, source_mode: str = "auto") -> dict[str, Any]:
    payload = get_options_factor_data(symbol, source_mode=source_mode)
    data = payload["data"]
    oi_ratio = compute_put_call_oi_ratio(data)
    volume_ratio = compute_put_call_volume_ratio(data)
    iv = compute_iv_proxy_signal(data)
    gamma = compute_gamma_proxy_signal(data)
    components = [value for value in [iv["score"], gamma["score"]] if value is not None]
    if oi_ratio is not None:
        components.append(max(0.0, min(100.0, 50 + (oi_ratio - 1) * 20)))
    if volume_ratio is not None:
        components.append(max(0.0, min(100.0, 50 + (volume_ratio - 1) * 20)))
    return {
        "symbol": symbol.upper(),
        "put_call_oi_ratio": oi_ratio,
        "put_call_volume_ratio": volume_ratio,
        "iv_proxy": iv,
        "gamma_proxy": gamma,
        "options_activity_score": round(sum(components) / max(1, len(components)), 1),
        "data_gaps": payload["data_gaps"],
        "source_confidence": payload["source_confidence"],
        "caveat": "Options factor outputs are research proxies unless official provider fields are present.",
    }
