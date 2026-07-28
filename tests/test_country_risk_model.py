from __future__ import annotations

from lib.country_risk_model import build_country_risk_cards, build_country_risk_table, compute_country_instability_score, compute_region_instability_score


SAMPLE_EVENTS = [
    {"title": "Missile alert near border", "country": "South Korea", "region": "Korea", "severity": "high", "freshness_status": "fresh"},
    {"title": "Cyber outage reported", "country": "South Korea", "region": "Korea", "severity": "elevated", "freshness_status": "estimated", "data_gap": "source confirmation pending"},
]


def test_country_risk_score_range_and_caveat():
    score = compute_country_instability_score("South Korea", SAMPLE_EVENTS)
    assert 0 <= score["instability_score"] <= 100
    assert "Heuristic" in score["caveat"]
    assert score["risk_level"] in {"low", "watch", "elevated", "high", "critical"}


def test_country_risk_table_cards_and_region():
    table = build_country_risk_table(SAMPLE_EVENTS)
    assert {"country", "iso3", "instability_score", "risk_level", "data_gaps"}.issubset(table.columns)
    cards = build_country_risk_cards(SAMPLE_EVENTS)
    assert cards
    region = compute_region_instability_score("Korea", SAMPLE_EVENTS)
    assert 0 <= region["instability_score"] <= 100
