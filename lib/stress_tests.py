from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .data_status import ok_result


DEFAULT_ASSET_BUCKETS = {
    "SPY": "equity",
    "QQQ": "equity",
    "IWM": "equity",
    "TLT": "rates",
    "IEF": "rates",
    "CL=F": "oil",
    "XLE": "oil_equity",
    "DX-Y.NYB": "usd",
    "BTC-USD": "crypto",
    "ETH-USD": "crypto",
    "^VIX": "volatility",
}


def _impact(tickers: list[str], weights: list[float], shocks: dict[str, float]) -> dict[str, Any]:
    if not tickers:
        tickers = list(DEFAULT_ASSET_BUCKETS.keys())[:3]
    if weights is None or len(weights) != len(tickers):
        weights = [1 / len(tickers)] * len(tickers)
    total = 0.0
    rows = []
    for ticker, weight in zip(tickers, weights):
        bucket = DEFAULT_ASSET_BUCKETS.get(ticker, "equity")
        shock = shocks.get(ticker, shocks.get(bucket, shocks.get("default", 0.0)))
        contribution = weight * shock
        total += contribution
        rows.append({"asset": ticker, "bucket": bucket, "weight": weight, "shock": shock, "impact": contribution})
    largest = sorted(rows, key=lambda row: abs(row["impact"]), reverse=True)[:3]
    return {"estimated_portfolio_impact": total, "contributors": rows, "largest_contributors": largest}


def _result(name: str, tickers: list[str], weights: list[float] | None, shocks: dict[str, float]) -> dict[str, Any]:
    impact = _impact(tickers, weights, shocks)
    return {
        "scenario": name,
        "affected_assets": ", ".join(tickers),
        "assumed_shocks": shocks,
        "estimated_portfolio_impact": impact["estimated_portfolio_impact"],
        "largest_contributors": impact["largest_contributors"],
        "caveat": "Scenario estimate; shocks are simplified and do not model path dependency.",
        "data_gaps": ["No live covariance shock transmission model in free mode."],
    }


def run_equity_selloff_stress(tickers: list[str], weights: list[float] | None = None) -> dict[str, Any]:
    return _result("Equity selloff stress", tickers, weights, {"equity": -0.12, "rates": 0.03, "oil": -0.06, "oil_equity": -0.08, "crypto": -0.18, "default": -0.05})


def run_rate_spike_stress(tickers: list[str], weights: list[float] | None = None) -> dict[str, Any]:
    return _result("Rate spike stress", tickers, weights, {"rates": -0.10, "equity": -0.05, "usd": 0.04, "crypto": -0.08, "default": -0.03})


def run_oil_shock_stress(tickers: list[str], weights: list[float] | None = None) -> dict[str, Any]:
    return _result("Oil shock stress", tickers, weights, {"oil": 0.18, "oil_equity": 0.10, "equity": -0.04, "rates": -0.02, "default": -0.02})


def run_usd_spike_stress(tickers: list[str], weights: list[float] | None = None) -> dict[str, Any]:
    return _result("USD spike stress", tickers, weights, {"usd": 0.08, "equity": -0.06, "oil": -0.08, "crypto": -0.12, "default": -0.04})


def run_crypto_deleveraging_stress(tickers: list[str], weights: list[float] | None = None) -> dict[str, Any]:
    return _result("Crypto deleveraging stress", tickers, weights, {"crypto": -0.30, "equity": -0.03, "default": -0.02})


def run_volatility_shock_stress(tickers: list[str], weights: list[float] | None = None) -> dict[str, Any]:
    return _result("Volatility shock stress", tickers, weights, {"volatility": 0.35, "equity": -0.10, "crypto": -0.16, "rates": 0.02, "default": -0.05})


def run_custom_stress_test(tickers: list[str], weights: list[float] | None = None, shocks: dict[str, float] | None = None) -> dict[str, Any]:
    return _result("Custom stress condition", tickers, weights, shocks or {"default": -0.05})


def build_stress_test_matrix(tickers: list[str] | None = None, weights: list[float] | None = None) -> tuple[pd.DataFrame, object]:
    tickers = tickers or ["SPY", "TLT", "CL=F", "BTC-USD"]
    scenarios = [
        run_equity_selloff_stress(tickers, weights),
        run_rate_spike_stress(tickers, weights),
        run_oil_shock_stress(tickers, weights),
        run_usd_spike_stress(tickers, weights),
        run_crypto_deleveraging_stress(tickers, weights),
        run_volatility_shock_stress(tickers, weights),
        run_custom_stress_test(tickers, weights),
    ]
    frame = pd.DataFrame(scenarios)
    return frame, ok_result(frame, source="stress test engine", provider="stress_tests", is_estimated=True, coverage=f"{len(frame)} stress scenarios")

