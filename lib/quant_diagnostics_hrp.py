from __future__ import annotations

from typing import Any
import math


def inverse_vol_weighting_diagnostic(returns_by_asset: dict[str, list[float]]) -> dict[str, Any]:
    vols = {}
    for asset, vals in returns_by_asset.items():
        xs = [float(x) for x in vals]
        if len(xs) < 2:
            vols[asset] = None
        else:
            mean = sum(xs) / len(xs)
            vols[asset] = math.sqrt(sum((x - mean) ** 2 for x in xs) / (len(xs) - 1))
    inv = {a: (0.0 if v in (None, 0) else 1.0 / float(v)) for a, v in vols.items()}
    total = sum(inv.values()) or 1.0
    weights = {a: inv[a] / total for a in inv}
    return {"ok": True, "volatility_by_asset": vols, "inverse_vol_weights_diagnostic": weights, "caveat": "diagnostic_weights_are_not_an_allocation_plan", "research_only": True}


def build_hrp_diagnostic(returns_by_asset: dict[str, list[float]]) -> dict[str, Any]:
    assets = list(returns_by_asset)
    tree = [{"cluster": "root", "children": assets, "method": "simple_asset_list", "research_only": True}]
    return {"ok": bool(assets), "risk_tree": tree, "inverse_vol": inverse_vol_weighting_diagnostic(returns_by_asset), "caveat": "HRP-inspired diagnostic only; no optimizer runtime", "research_only": True}
