from __future__ import annotations
from typing import Any
import numpy as np


def correlation_matrix(returns_by_asset: dict[str, list[float]]) -> dict[str, Any]:
    assets=list(returns_by_asset.keys())
    if not assets: return {'ok': False, 'error': 'no_assets', 'research_only': True}
    min_len=min(len(v) for v in returns_by_asset.values())
    if min_len < 2: return {'ok': False, 'error': 'insufficient_observations', 'research_only': True}
    arr=np.array([returns_by_asset[a][-min_len:] for a in assets], dtype=float)
    corr=np.corrcoef(arr)
    return {'ok': True, 'assets': assets, 'matrix': corr.tolist(), 'research_only': True}


def eigenvalue_summary(correlation_payload: dict[str, Any]) -> dict[str, Any]:
    if not correlation_payload.get('ok'): return {'ok': False, 'error': correlation_payload.get('error'), 'research_only': True}
    vals=np.linalg.eigvalsh(np.array(correlation_payload['matrix'], dtype=float))
    return {'ok': True, 'eigenvalues': sorted([float(v) for v in vals], reverse=True), 'largest_eigenvalue': float(max(vals)), 'smallest_eigenvalue': float(min(vals)), 'research_only': True}


def rmt_noise_threshold_caveat(num_assets: int, observations: int) -> dict[str, Any]:
    q = observations / max(num_assets, 1)
    lambda_plus = (1 + (1 / q) ** 0.5) ** 2 if q > 0 else None
    return {'threshold_concept': lambda_plus, 'caveat': 'RMT-style threshold is concept-only and not a cleaned covariance model.', 'research_only': True}


def build_correlation_diagnostics(returns_by_asset: dict[str, list[float]]) -> dict[str, Any]:
    corr=correlation_matrix(returns_by_asset); eig=eigenvalue_summary(corr)
    obs=min([len(v) for v in returns_by_asset.values()], default=0)
    return {'ok': corr.get('ok', False), 'correlation': corr, 'eigen': eig, 'rmt_caveat': rmt_noise_threshold_caveat(len(returns_by_asset), obs), 'research_only': True}
