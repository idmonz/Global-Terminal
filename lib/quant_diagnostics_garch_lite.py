from __future__ import annotations

from typing import Any
from .quant_diagnostics_volatility import ewma_volatility, volatility_clustering_score


def garch_lite_diagnostic(returns: list[float]) -> dict[str, Any]:
    vals = [float(x) for x in returns]
    ewma = ewma_volatility(vals)
    sq = [x * x for x in vals]
    clustering = volatility_clustering_score(vals)
    squared_clustering = volatility_clustering_score(sq) if len(sq) > 3 else None
    return {"ok": True, "ewma_last": ewma[-1] if ewma else None, "absolute_return_clustering": clustering, "squared_return_clustering": squared_clustering, "caveat": "GARCH-lite compares clustering proxies without fitting a heavy model", "research_only": True}
