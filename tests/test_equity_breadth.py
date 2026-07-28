from __future__ import annotations

import pandas as pd

from lib.equity_breadth import (
    build_breadth_snapshot,
    compute_above_moving_average_percent,
    compute_index_breadth_snapshot,
    validate_universe_schema,
)


def _history(values):
    return pd.DataFrame({"close": values, "volume": range(len(values))})


def test_breadth_schema_and_ma_calculation():
    histories = {"A": _history(range(1, 101)), "B": _history(list(range(100, 0, -1)))}
    pct = compute_above_moving_average_percent(histories, window=20)
    assert pct == 50.0

    universe = pd.DataFrame({"ticker": ["A", "B"], "company": ["A", "B"], "sector": ["Tech", "Energy"], "market_cap": [2, 1]})
    snapshot = build_breadth_snapshot(universe, histories, "unit")
    assert snapshot["symbols_total"] == 2
    assert snapshot["symbols_valid"] == 2
    assert "breadth_regime" in snapshot


def test_breadth_partial_failure_handling():
    histories = {"A": _history(range(1, 101)), "B": pd.DataFrame()}
    universe = pd.DataFrame({"ticker": ["A", "B"], "company": ["A", "B"], "sector": ["Tech", "Energy"]})
    snapshot, status = compute_index_breadth_snapshot("sp500", histories=histories)
    assert status.ok
    assert snapshot["symbols_valid"] == 1
    assert snapshot["data_gaps"]


def test_validate_universe_schema():
    valid, missing = validate_universe_schema(pd.DataFrame({"ticker": ["A"]}))
    assert not valid
    assert "company" in missing

