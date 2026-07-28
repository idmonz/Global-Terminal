from __future__ import annotations

from lib.summary_keyword_engine import build_actionable_summary_phrases, build_keyword_chips, classify_keyword_importance, extract_summary_keywords


def test_summary_keyword_engine_classifies_useful_categories():
    payload = {"summary": "BTC funding stress, Red Sea energy risk, provider key missing, stale data"}
    keywords = extract_summary_keywords(payload)
    categories = {item["category"] for item in keywords}
    assert {"crypto stress", "energy/geopolitics", "provider issue"} & categories
    assert classify_keyword_importance("stale source")["category"] == "data freshness"
    assert build_keyword_chips(keywords)[0]["tooltip"]
    assert build_actionable_summary_phrases(payload)
