from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .openbb_macro_backend import build_macro_rates_dashboard_payload


def get_rates_factor_data(*, source_mode: str = "auto") -> dict[str, Any]:
    payload = build_macro_rates_dashboard_payload(source_mode=source_mode)
    return {"payload": payload, "status_table": payload["status_table"], "data_gaps": payload["data_gaps"], "source_confidence": payload["source_confidence"]}


def compute_duration_regime_signal(rates_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    confidence = float((rates_payload or {}).get("source_confidence", 0) or 0)
    return {"factor": "duration", "score": round(max(0.0, min(100.0, confidence)), 1), "label": "duration regime proxy", "caveat": "Duration signal is proxy-based."}


def compute_curve_regime_signal(rates_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"factor": "curve", "score": float((rates_payload or {}).get("source_confidence", 0) or 0), "label": "curve regime proxy", "caveat": "Curve shape depends on available rates data."}


def compute_real_yield_proxy_signal(rates_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"factor": "real_yield_proxy", "score": max(0.0, float((rates_payload or {}).get("source_confidence", 0) or 0) - 10), "label": "real yield proxy", "caveat": "Real yield signal may use ETF/rates proxies."}


def compute_credit_spread_proxy_signal(rates_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    gaps = len((rates_payload or {}).get("data_gaps", []))
    return {"factor": "credit_spread_proxy", "score": round(max(0.0, 70.0 - gaps * 5), 1), "label": "credit spread proxy", "caveat": "Credit spread signal may rely on proxy ETFs or optional FRED/OpenBB data."}


def build_rates_macro_factor_scores(*, source_mode: str = "auto") -> dict[str, Any]:
    data = get_rates_factor_data(source_mode=source_mode)
    signals = [
        compute_duration_regime_signal(data),
        compute_curve_regime_signal(data),
        compute_real_yield_proxy_signal(data),
        compute_credit_spread_proxy_signal(data),
    ]
    return {
        "signals": signals,
        "score": round(sum(signal["score"] for signal in signals) / max(1, len(signals)), 1),
        "data_gaps": data["data_gaps"],
        "source_confidence": data["source_confidence"],
        "caveat": "Rates/macro factors are contextual research features.",
    }
