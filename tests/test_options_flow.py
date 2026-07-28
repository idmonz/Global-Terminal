from __future__ import annotations

import pandas as pd

from lib.options_flow import (
    GAMMA_CAVEAT,
    compute_gamma_exposure_proxy,
    compute_largest_oi_strikes,
    compute_max_pain_proxy,
    compute_put_call_oi_ratio,
    compute_put_call_volume_ratio,
)


def _chains():
    calls = pd.DataFrame(
        {
            "strike": [95, 100, 105],
            "openInterest": [100, 250, 150],
            "volume": [10, 20, 30],
            "impliedVolatility": [0.25, 0.22, 0.24],
        }
    )
    puts = pd.DataFrame(
        {
            "strike": [95, 100, 105],
            "openInterest": [120, 180, 220],
            "volume": [12, 18, 22],
            "impliedVolatility": [0.28, 0.24, 0.26],
        }
    )
    return calls, puts


def test_put_call_ratios_and_largest_oi():
    calls, puts = _chains()
    assert round(compute_put_call_oi_ratio(calls, puts), 2) == 1.04
    assert round(compute_put_call_volume_ratio(calls, puts), 2) == 0.87
    largest = compute_largest_oi_strikes(calls, puts, top_n=2)
    assert len(largest) == 2
    assert "side" in largest.columns


def test_gamma_proxy_schema_and_caveat():
    calls, puts = _chains()
    gamma = compute_gamma_exposure_proxy(calls, puts, underlying_price=100.0, expiry="2026-12-18")
    required = {"strike", "side", "gamma_proxy", "open_interest", "method", "caveat"}
    assert required.issubset(gamma.columns)
    assert gamma["caveat"].str.contains(GAMMA_CAVEAT, regex=False).all()
    max_pain = compute_max_pain_proxy(calls, puts)
    assert max_pain["max_pain_strike"] is not None
