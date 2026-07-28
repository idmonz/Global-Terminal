from __future__ import annotations

import pandas as pd

from lib.market_impact_engine import build_event_to_scenario_evidence, build_market_impact_cards, build_news_market_impact_table, compute_recent_asset_reaction


def _prices():
    idx = pd.date_range("2026-01-01", periods=30, freq="D")
    return pd.DataFrame({"Close": [100 + i for i in range(30)], "Volume": [1000 + i * 10 for i in range(30)]}, index=idx)


def test_market_impact_engine_proxy_labels():
    event = {"event_id": "e1", "title": "Fed inflation rates update", "region": "Americas", "severity": "high"}
    table, status = build_news_market_impact_table([event], price_data={"TLT": _prices(), "SPY": _prices(), "DXY": _prices()})
    assert not table.empty
    assert table["causality_caveat"].str.contains("Correlation/proxy").all()
    assert table["evidence_language"].isin(["Observed related market move", "Data gap"]).all()
    cards = build_market_impact_cards([event], table)
    assert cards and "causal" in cards[0]["bullets"][1]


def test_recent_asset_reaction_data_gap_is_soft_status():
    reaction, status = compute_recent_asset_reaction("ZZZ", price_data=None, fetch_market_data=False)
    assert reaction["reaction_label"] == "Data gap"
    assert status.ok
    assert status.is_estimated
    assert "Price history unavailable" in status.warning


def test_scenario_evidence_schema():
    event = {"event_id": "e1", "title": "Crypto regulation ETF update", "region": "Global", "severity": "watch"}
    evidence = build_event_to_scenario_evidence([event])
    assert {"news_impact_evidence", "related_assets", "catalyst_clusters", "confidence_caveat"}.issubset(evidence.columns)
