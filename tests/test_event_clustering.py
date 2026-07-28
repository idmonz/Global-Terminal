from __future__ import annotations

from datetime import datetime, timezone

from lib.event_clustering import cluster_news_by_asset, cluster_news_by_keyword, cluster_news_by_region, build_event_cluster_cards


SAMPLE_NEWS = [
    {
        "title": "Hormuz tanker attack lifts oil shipping risk",
        "summary": "WTI and Brent route risk remains elevated.",
        "source": "reuters.com",
        "published_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "Hormuz shipping insurance costs rise after attack",
        "summary": "Energy desks monitor tanker route pressure.",
        "source": "example.com",
        "published_at": datetime.now(timezone.utc).isoformat(),
    },
]


def test_event_clustering_outputs_cards():
    keyword = cluster_news_by_keyword(SAMPLE_NEWS)
    region = cluster_news_by_region(SAMPLE_NEWS)
    asset = cluster_news_by_asset(SAMPLE_NEWS)
    cards = build_event_cluster_cards(SAMPLE_NEWS)

    assert not keyword.empty
    assert not region.empty
    assert not asset.empty
    assert cards
    assert all("method" in card for card in cards)
