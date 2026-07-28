from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _asset_names(data: Any) -> list[str]:
    if isinstance(data, pd.DataFrame):
        return [str(col) for col in data.columns]
    if isinstance(data, (list, tuple, set)):
        return [str(item) for item in data]
    return []


def _normalize(weights: np.ndarray, *, allow_short: bool = False) -> np.ndarray:
    weights = np.array(weights, dtype=float)
    if not allow_short:
        weights = np.clip(weights, 0.0, None)
    total = float(weights.sum())
    if total == 0:
        return np.repeat(1.0 / len(weights), len(weights)) if len(weights) else weights
    return weights / total


def _returns_frame(returns: pd.DataFrame | None) -> pd.DataFrame:
    if returns is None or getattr(returns, "empty", True):
        return pd.DataFrame()
    return returns.apply(pd.to_numeric, errors="coerce").dropna(how="all")


def equal_weight(assets: list[str] | pd.DataFrame) -> dict[str, float]:
    names = _asset_names(assets)
    if not names:
        return {}
    return {name: 1.0 / len(names) for name in names}


def inverse_volatility_weight(returns: pd.DataFrame | pd.Series | dict[str, float], *, floor: float = 1e-6) -> dict[str, float]:
    if isinstance(returns, dict):
        vol = pd.Series(returns, dtype=float)
    elif isinstance(returns, pd.Series):
        vol = returns.astype(float)
    else:
        frame = _returns_frame(returns)
        vol = frame.std() if not frame.empty else pd.Series(dtype=float)
    vol = vol.replace([np.inf, -np.inf], np.nan).dropna().clip(lower=floor)
    if vol.empty:
        return {}
    inv = 1.0 / vol
    weights = inv / inv.sum()
    return weights.to_dict()


def cap_weight_limits(weights: dict[str, float], *, max_weight_per_asset: float = 1.0, min_weight_per_asset: float = 0.0) -> dict[str, float]:
    if not weights:
        return {}
    capped = {asset: min(max(float(weight), min_weight_per_asset), max_weight_per_asset) for asset, weight in weights.items()}
    total = sum(capped.values())
    if total <= 0:
        return equal_weight(list(weights))
    return {asset: weight / total for asset, weight in capped.items()}


def apply_weight_constraints(
    weights: dict[str, float],
    *,
    max_weight_per_asset: float = 1.0,
    min_weight_per_asset: float = 0.0,
    allow_short: bool = False,
    cash_weight: float = 0.0,
    asset_class_limits: dict[str, float] | None = None,
    region_limits: dict[str, float] | None = None,
    metadata: dict[str, dict[str, Any]] | None = None,
) -> dict[str, float]:
    metadata = metadata or {}
    if not allow_short:
        weights = {asset: max(0.0, float(weight)) for asset, weight in weights.items()}
    constrained = cap_weight_limits(weights, max_weight_per_asset=max_weight_per_asset, min_weight_per_asset=min_weight_per_asset)
    for limits, key in [(asset_class_limits or {}, "asset_class"), (region_limits or {}, "region")]:
        for group, limit in limits.items():
            members = [asset for asset in constrained if metadata.get(asset, {}).get(key) == group]
            exposure = sum(constrained[asset] for asset in members)
            if members and exposure > float(limit):
                scale = float(limit) / exposure
                for asset in members:
                    constrained[asset] *= scale
    investable = max(0.0, 1.0 - max(0.0, min(1.0, float(cash_weight))))
    total = sum(constrained.values())
    if total > 0:
        constrained = {asset: weight / total * investable for asset, weight in constrained.items()}
    if cash_weight > 0:
        constrained["CASH"] = max(0.0, min(1.0, float(cash_weight)))
    return constrained


def _optimize(returns: pd.DataFrame, objective, *, max_weight_per_asset: float = 1.0, allow_short: bool = False) -> tuple[np.ndarray, str | None]:
    frame = _returns_frame(returns)
    n_assets = len(frame.columns)
    if n_assets == 0:
        return np.array([]), "No return frame supplied."
    try:
        from scipy.optimize import minimize

        bounds = [(-max_weight_per_asset if allow_short else 0.0, max_weight_per_asset) for _ in range(n_assets)]
        constraints = [{"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0}]
        result = minimize(objective, np.repeat(1 / n_assets, n_assets), method="SLSQP", bounds=bounds, constraints=constraints)
        if not result.success:
            return _normalize(np.repeat(1 / n_assets, n_assets), allow_short=allow_short), result.message
        return _normalize(result.x, allow_short=allow_short), None
    except Exception as exc:
        return _normalize(np.repeat(1 / n_assets, n_assets), allow_short=allow_short), str(exc)


def min_variance_weight(returns: pd.DataFrame, *, max_weight_per_asset: float = 1.0, allow_short: bool = False) -> dict[str, float]:
    frame = _returns_frame(returns)
    if frame.empty:
        return {}
    cov = frame.cov().to_numpy()
    weights, _ = _optimize(frame, lambda w: float(w.T @ cov @ w), max_weight_per_asset=max_weight_per_asset, allow_short=allow_short)
    return dict(zip(frame.columns, weights))


def max_sharpe_proxy_weight(returns: pd.DataFrame, *, risk_free_rate: float = 0.0, max_weight_per_asset: float = 1.0, allow_short: bool = False) -> dict[str, float]:
    frame = _returns_frame(returns)
    if frame.empty:
        return {}
    mean = frame.mean().to_numpy() - risk_free_rate / 252
    cov = frame.cov().to_numpy()

    def objective(weights):
        vol = np.sqrt(float(weights.T @ cov @ weights))
        if vol <= 0:
            return 1e9
        return -float(weights @ mean / vol)

    weights, warning = _optimize(frame, objective, max_weight_per_asset=max_weight_per_asset, allow_short=allow_short)
    if warning:
        return inverse_volatility_weight(frame)
    return dict(zip(frame.columns, weights))


def risk_parity_proxy_weight(returns: pd.DataFrame, *, max_weight_per_asset: float = 1.0) -> dict[str, float]:
    return cap_weight_limits(inverse_volatility_weight(returns), max_weight_per_asset=max_weight_per_asset)


def max_diversification_proxy_weight(returns: pd.DataFrame, *, max_weight_per_asset: float = 1.0) -> dict[str, float]:
    frame = _returns_frame(returns)
    if frame.empty:
        return {}
    corr_penalty = frame.corr().abs().mean().replace(0, np.nan)
    vol = frame.std().replace(0, np.nan)
    score = (1.0 / vol) * (1.0 / corr_penalty)
    score = score.replace([np.inf, -np.inf], np.nan).dropna()
    if score.empty:
        return equal_weight(frame)
    weights = (score / score.sum()).to_dict()
    return cap_weight_limits(weights, max_weight_per_asset=max_weight_per_asset)


def volatility_target_weight(weights: dict[str, float], returns: pd.DataFrame, *, target_volatility: float = 0.10) -> dict[str, float]:
    if not weights:
        return {}
    frame = _returns_frame(returns)
    aligned = [asset for asset in weights if asset in frame.columns]
    if frame.empty or not aligned:
        return weights
    vector = np.array([weights[asset] for asset in aligned], dtype=float)
    cov = frame[aligned].cov().to_numpy() * 252
    current_vol = np.sqrt(float(vector.T @ cov @ vector))
    if current_vol <= 0:
        return weights
    scale = min(1.0, max(0.0, target_volatility / current_vol))
    scaled = {asset: weights[asset] * scale for asset in weights}
    scaled["CASH"] = scaled.get("CASH", 0.0) + (1.0 - sum(scaled.values()))
    return cap_weight_limits(scaled)


def optimize_portfolio_candidates(
    returns: pd.DataFrame,
    *,
    max_weight_per_asset: float = 0.40,
    cash_weight: float = 0.0,
    target_volatility: float = 0.10,
) -> pd.DataFrame:
    frame = _returns_frame(returns)
    methods = {
        "Equal Weight": equal_weight(frame),
        "Inverse Volatility": inverse_volatility_weight(frame),
        "Min Variance Proxy": min_variance_weight(frame, max_weight_per_asset=max_weight_per_asset),
        "Max Sharpe Proxy": max_sharpe_proxy_weight(frame, max_weight_per_asset=max_weight_per_asset),
        "Risk Parity Proxy": risk_parity_proxy_weight(frame, max_weight_per_asset=max_weight_per_asset),
        "Max Diversification Proxy": max_diversification_proxy_weight(frame, max_weight_per_asset=max_weight_per_asset),
    }
    methods["Volatility Target Proxy"] = volatility_target_weight(methods["Inverse Volatility"], frame, target_volatility=target_volatility)
    rows = []
    for name, weights in methods.items():
        constrained = apply_weight_constraints(weights, max_weight_per_asset=max_weight_per_asset, cash_weight=cash_weight)
        rows.append({"candidate": name, "weights": constrained, "max_weight": max(constrained.values()) if constrained else 0.0, "cash_weight": constrained.get("CASH", 0.0), "caveat": "Research candidate generated from historical/proxy data."})
    return pd.DataFrame(rows)
