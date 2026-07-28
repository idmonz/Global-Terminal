from __future__ import annotations

from typing import Any
import numpy as np
from .quant_diagnostics_correlation import correlation_matrix


def eigenvalue_noise_threshold(num_assets: int, observations: int) -> dict[str, Any]:
    if num_assets <= 0 or observations <= 0:
        return {"ok": False, "lambda_plus": None, "lambda_minus": None, "research_only": True}
    q = observations / max(num_assets, 1)
    root = (1 / q) ** 0.5 if q > 0 else 0.0
    return {"ok": True, "lambda_plus": (1 + root) ** 2, "lambda_minus": (1 - root) ** 2, "q": q, "research_only": True}


def build_rmt_diagnostic(returns_by_asset: dict[str, list[float]]) -> dict[str, Any]:
    corr = correlation_matrix(returns_by_asset)
    if not corr.get("ok"):
        return {"ok": False, "error": corr.get("error"), "research_only": True}
    vals = np.linalg.eigvalsh(np.array(corr["matrix"], dtype=float)).tolist()
    obs = min(len(v) for v in returns_by_asset.values())
    threshold = eigenvalue_noise_threshold(len(returns_by_asset), obs)
    noisy = [float(v) for v in vals if threshold.get("lambda_plus") is not None and float(v) <= float(threshold["lambda_plus"])]
    return {"ok": True, "eigenvalues": sorted([float(v) for v in vals], reverse=True), "threshold": threshold, "noise_eigenvalue_count": len(noisy), "cleaned_correlation_diagnostic": corr["matrix"], "caveat": "RMT diagnostic labels noise bands only; it is not an optimizer", "research_only": True}
