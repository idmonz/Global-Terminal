from __future__ import annotations

from lib.stress_tests import build_stress_test_matrix


def test_stress_matrix_schema():
    frame, status = build_stress_test_matrix(["SPY", "TLT"], [0.6, 0.4])
    assert status.ok
    assert len(frame) == 7
    assert {"scenario", "estimated_portfolio_impact", "largest_contributors", "data_gaps"}.issubset(frame.columns)

