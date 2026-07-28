from __future__ import annotations
import math
from typing import Any


def simple_returns(prices: list[float]) -> list[float]:
    vals=[float(x) for x in prices]
    return [(vals[i]/vals[i-1]-1.0) for i in range(1,len(vals)) if vals[i-1] != 0]


def log_returns(prices: list[float]) -> list[float]:
    vals=[float(x) for x in prices]
    return [math.log(vals[i]/vals[i-1]) for i in range(1,len(vals)) if vals[i-1] > 0 and vals[i] > 0]


def rolling_mean(values: list[float], window: int) -> list[float | None]:
    out=[]; vals=[float(x) for x in values]; w=max(1,int(window))
    for i in range(len(vals)):
        if i+1<w: out.append(None)
        else: out.append(sum(vals[i+1-w:i+1])/w)
    return out


def rolling_volatility(values: list[float], window: int, annualization: float = 252.0) -> list[float | None]:
    out=[]; vals=[float(x) for x in values]; w=max(2,int(window))
    for i in range(len(vals)):
        if i+1<w: out.append(None)
        else:
            sample=vals[i+1-w:i+1]; mean=sum(sample)/w; var=sum((x-mean)**2 for x in sample)/(w-1)
            out.append(math.sqrt(var)*math.sqrt(annualization))
    return out


def build_returns_diagnostics(prices: list[float], window: int = 5) -> dict[str, Any]:
    sr=simple_returns(prices); lr=log_returns(prices)
    return {'ok': True, 'simple_returns': sr, 'log_returns': lr, 'rolling_mean': rolling_mean(sr, window), 'rolling_volatility': rolling_volatility(sr, window), 'caveat': 'supplied_price_series_only_no_prediction_claim', 'research_only': True}
