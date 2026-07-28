from __future__ import annotations

import pandas as pd

from lib.catalyst_graph import build_catalyst_graph
from lib.impact_visuals import asset_reaction_bar_chart, catalyst_sankey_chart, event_asset_heatmap, event_timeline_with_market_overlay, market_impact_matrix_chart, scenario_evidence_contribution_chart


IMPACT_ROWS = pd.DataFrame(
    [
        {"event_id": "e1", "event_title": "Fed rates", "ticker": "TLT", "relevance_score": 80, "return_1d_pct": -1.2, "asset_class": "rates"},
        {"event_id": "e1", "event_title": "Fed rates", "ticker": "DXY", "relevance_score": 70, "return_1d_pct": 0.5, "asset_class": "FX"},
    ]
)


def test_impact_visuals_return_figures():
    fig, frame, status = market_impact_matrix_chart(IMPACT_ROWS)
    assert fig is not None
    heatmap, _, heatmap_status = event_asset_heatmap(IMPACT_ROWS)
    assert heatmap is not None
    reaction, _, reaction_status = asset_reaction_bar_chart(IMPACT_ROWS)
    assert reaction is not None
    assert status.ok and heatmap_status.ok and reaction_status.ok


def test_asset_reaction_chart_falls_back_to_relevance_when_prices_missing():
    missing_price_rows = IMPACT_ROWS.copy()
    missing_price_rows["return_1d_pct"] = None
    fig, frame, status = asset_reaction_bar_chart(missing_price_rows)
    assert fig is not None
    assert status.ok
    assert "relevance" in status.warning.lower()
    assert "relevance_score" in frame.columns


def test_catalyst_and_scenario_visuals():
    events = [{"event_id": "e1", "title": "Fed rates", "timestamp": "2026-01-10T00:00:00Z", "region": "Americas"}]
    graph = build_catalyst_graph(events, IMPACT_ROWS)
    sankey, _, sankey_status = catalyst_sankey_chart(graph)
    assert sankey is not None
    timeline, _, timeline_status = event_timeline_with_market_overlay(events, IMPACT_ROWS)
    assert timeline is not None
    evidence = pd.DataFrame([{"event_id": "e1", "event_title": "Fed rates", "news_impact_evidence": 45}])
    evidence_fig, _, evidence_status = scenario_evidence_contribution_chart(evidence)
    assert evidence_fig is not None
    assert sankey_status.ok and timeline_status.ok and evidence_status.ok
