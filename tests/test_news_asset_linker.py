from __future__ import annotations

from lib.news_asset_linker import build_related_asset_list, classify_event_domain, classify_market_channel, extract_entities_from_news, score_asset_relevance


def test_known_geopolitical_keyword_mapping():
    item = {"title": "Iran Hormuz tanker sanctions lift oil risk", "region": "Middle East"}
    assets = build_related_asset_list(item)
    tickers = {ticker for row in assets for ticker in row["related_tickers"]}
    assert {"CL=F", "BZ=F", "XLE", "DXY", "^VIX"}.issubset(tickers)
    assert classify_event_domain(item) in {"oil", "geopolitics"}
    assert "commodities" in classify_market_channel(item) or "energy" in classify_market_channel(item)


def test_entity_extraction_and_relevance_score():
    item = "Taiwan China semiconductor export controls near TSMC"
    entities = extract_entities_from_news(item)
    assert "Taiwan" in entities["countries"]
    relevance = score_asset_relevance(item, "TSM")
    assert relevance["relevance_score"] > 0
