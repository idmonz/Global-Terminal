from __future__ import annotations

from typing import Any
from .quant_diagnostics_mean_reversion import pair_residual_diagnostic


def cointegration_diagnostic(left: list[float], right: list[float]) -> dict[str, Any]:
    base = pair_residual_diagnostic(left, right)
    if not base.get("ok"):
        return base
    try:
        from statsmodels.tsa.stattools import adfuller, coint  # type: ignore
        residual = []
        n = min(len(left), len(right))
        beta = float(base["beta"]); alpha = float(base["alpha"])
        for l, r in zip(left[-n:], right[-n:]):
            residual.append(float(l) - beta * float(r) - alpha)
        adf = adfuller(residual, autolag="AIC")
        ct = coint(left[-n:], right[-n:])
        return {**base, "statsmodels_available": True, "adf_stat": float(adf[0]), "adf_pvalue": float(adf[1]), "coint_stat": float(ct[0]), "coint_pvalue": float(ct[1]), "pvalue_caveat": "p-values depend on optional statsmodels and supplied sample", "research_only": True}
    except Exception:
        return {**base, "statsmodels_available": False, "pvalue_caveat": "statsmodels unavailable; residual diagnostic has no p-value", "research_only": True}
