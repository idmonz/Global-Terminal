from __future__ import annotations

import pandas as pd

from lib.performance_attribution import build_attribution_report


def test_performance_attribution_tables_exist():
    returns = pd.DataFrame({"AAA": [0.01, -0.02, 0.03], "BBB": [0.0, 0.01, -0.01]})
    report = build_attribution_report(returns, {"AAA": 0.6, "BBB": 0.4}, metadata={"AAA": {"asset_class": "stock"}, "BBB": {"asset_class": "ETF"}})

    assert not report["return_contribution"].empty
    assert not report["risk_contribution"].empty
    assert "drawdown_contribution" in report
    assert report["caveat"]
