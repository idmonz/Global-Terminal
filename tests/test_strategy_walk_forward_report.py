from __future__ import annotations

from lib.strategy_walk_forward_report import build_strategy_walk_forward_report


def test_walk_forward_report_includes_overfit_caveat():
    report = build_strategy_walk_forward_report([0.01, -0.02, 0.03, 0.01])
    assert "overfit" in report["caveat"].lower()
