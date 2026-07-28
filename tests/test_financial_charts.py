from __future__ import annotations

import pandas as pd

from lib.financial_charts import data_availability_heatmap, eps_reported_estimate_chart, revenue_breakdown_chart, revenue_net_income_chart


def test_financial_chart_returns_figure_for_reported_data():
    income = pd.DataFrame({"revenue": [100.0, 120.0], "net_income": [10.0, 12.0]}, index=pd.to_datetime(["2024-12-31", "2025-12-31"]))
    fig, frame, status = revenue_net_income_chart(income)
    assert fig is not None
    assert status.ok


def test_no_fabricated_forecast_or_segment_values():
    fig, frame, status = eps_reported_estimate_chart(pd.DataFrame({"eps_actual": [1.2]}))
    assert fig is None
    assert not status.ok
    seg_fig, seg_frame, seg_status = revenue_breakdown_chart(pd.DataFrame())
    assert seg_fig is None
    assert "Real segment revenue data is unavailable" in seg_status.error


def test_data_availability_heatmap():
    fig, frame, status = data_availability_heatmap(pd.DataFrame([{"field": "income.revenue", "available": True}, {"field": "earnings.estimate", "available": False}]))
    assert fig is not None
    assert status.ok
