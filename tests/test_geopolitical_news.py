from __future__ import annotations

import pandas as pd

from lib.geopolitical_news import classify_geopolitical_news, compute_news_risk_score, dedupe_news_items, fetch_public_rss_news


def test_news_classifier():
    assert classify_geopolitical_news({"title": "Tanker disruption near Strait of Hormuz"}) in {"tanker", "chokepoint"}
    assert classify_geopolitical_news({"title": "Central bank meeting"}) == "unknown"


def test_dedupe_and_risk_score():
    items = pd.DataFrame([{"title": "Hormuz tanker risk", "url": "u", "classification": "chokepoint"}, {"title": "Hormuz tanker risk", "url": "u", "classification": "chokepoint"}])
    deduped = dedupe_news_items(items)
    assert len(deduped) == 1
    score = compute_news_risk_score(deduped)
    assert score["score"] > 0


def test_public_rss_parser_handles_rss_and_atom(monkeypatch):
    class Response:
        status_code = 200
        content = b""

        def __init__(self, content: bytes):
            self.content = content

        def raise_for_status(self):
            return None

    rss = b"""<?xml version="1.0"?><rss><channel><item><title>EIA oil inventories rise</title><link>https://eia.gov/a</link><pubDate>Wed, 10 Jun 2026 09:00:00 EST</pubDate><description>Official energy update.</description></item></channel></rss>"""
    atom = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Fed policy statement</title><link href="https://federalreserve.gov/b"/><updated>2026-06-10T14:00:00Z</updated><summary>Official macro update.</summary></entry></feed>"""

    def fake_get(url, **kwargs):
        return Response(atom if "fed" in url else rss)

    monkeypatch.setattr("lib.geopolitical_news.requests.get", fake_get)
    frame, status = fetch_public_rss_news(["https://www.eia.gov/rss/todayinenergy.xml", "https://fed.example/rss.xml"])
    assert status.ok
    assert len(frame) == 2
    assert {"title", "summary", "published_at", "credibility"}.issubset(frame.columns)
