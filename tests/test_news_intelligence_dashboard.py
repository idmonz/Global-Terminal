from __future__ import annotations

from lib.news_intelligence_dashboard import build_news_dashboard_payload, classify_news_by_theme, link_news_to_assets, link_news_to_regions


def test_news_intelligence_dashboard_links_themes_assets_regions():
    item = {"title": "Red Sea oil shipping risk hits markets", "region": "MENA", "source": "unit"}
    assert "energy" in classify_news_by_theme(item)
    assert "CL=F" in link_news_to_assets(item)
    assert "MENA" in link_news_to_regions(item)
    payload = build_news_dashboard_payload([item], [{"source": "unit", "status": "fresh"}])
    assert payload["timeline"]
    assert payload["heatmap"]["tiles"]
    assert payload["source_freshness"][0]["freshness"] == "fresh"
