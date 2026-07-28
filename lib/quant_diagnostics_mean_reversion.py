from __future__ import annotations
import math
from typing import Any
import numpy as np


def hurst_exponent(series: list[float], max_lag: int = 20) -> float | None:
    vals=np.array(series, dtype=float)
    if len(vals) < max_lag + 2: return None
    lags=range(2, max_lag)
    tau=[]
    for lag in lags:
        diff=vals[lag:]-vals[:-lag]
        std=float(np.std(diff))
        if std > 0: tau.append((math.log(lag), math.log(std)))
    if len(tau) < 2: return None
    x=np.array([p[0] for p in tau]); y=np.array([p[1] for p in tau])
    slope=float(np.polyfit(x,y,1)[0])
    return slope


def ou_half_life(series: list[float]) -> float | None:
    vals=np.array(series, dtype=float)
    if len(vals) < 3: return None
    y=vals[1:]-vals[:-1]
    x=vals[:-1]-float(np.mean(vals[:-1]))
    denom=float(np.dot(x,x))
    if denom == 0: return None
    beta=float(np.dot(x,y)/denom)
    if beta >= 0: return None
    return float(-math.log(2)/beta)


def pair_residual_diagnostic(left: list[float], right: list[float]) -> dict[str, Any]:
    n=min(len(left), len(right))
    if n < 3: return {'ok': False, 'error': 'insufficient_observations', 'research_only': True}
    x=np.array(right[-n:], dtype=float); y=np.array(left[-n:], dtype=float)
    x1=np.vstack([x, np.ones(n)]).T
    beta, alpha = np.linalg.lstsq(x1, y, rcond=None)[0]
    residual=(y-(beta*x+alpha)).tolist()
    return {'ok': True, 'beta': float(beta), 'alpha': float(alpha), 'residual_last': float(residual[-1]), 'residual_std': float(np.std(residual)), 'caveat': 'Residual diagnostic only; no dependency-required cointegration conclusion.', 'research_only': True}


def build_mean_reversion_diagnostics(series: list[float]) -> dict[str, Any]:
    return {'ok': True, 'hurst_exponent': hurst_exponent(series), 'ou_half_life': ou_half_life(series), 'stationarity_caveat': 'Simple estimators are diagnostic only and are not trading signals.', 'research_only': True}
