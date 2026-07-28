from __future__ import annotations
import math
from typing import Any


def ewma_volatility(returns: list[float], lambda_: float = 0.94, annualization: float = 252.0) -> list[float]:
    vals=[float(x) for x in returns]
    if not vals: return []
    var=vals[0]*vals[0]
    out=[]
    for r in vals:
        var=lambda_*var+(1-lambda_)*r*r
        out.append(math.sqrt(max(var,0.0))*math.sqrt(annualization))
    return out


def volatility_clustering_score(returns: list[float], lag: int = 1) -> float | None:
    vals=[abs(float(x)) for x in returns]
    if len(vals) <= lag + 1: return None
    x=vals[:-lag]; y=vals[lag:]
    mx=sum(x)/len(x); my=sum(y)/len(y)
    den=(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))**0.5
    return None if den == 0 else sum((a-mx)*(b-my) for a,b in zip(x,y))/den


def build_volatility_diagnostics(returns: list[float]) -> dict[str, Any]:
    return {'ok': True, 'ewma_volatility': ewma_volatility(returns), 'volatility_clustering_score': volatility_clustering_score(returns), 'garch_placeholder_caveat': 'GARCH is documented as a future optional diagnostic; no heavy runtime is required here.', 'research_only': True}
