from __future__ import annotations

import json

from lib.feed_registry import (
    FEED_REGISTRY_SCHEMA,
    build_feed_registry,
    default_rss_feed_urls,
    feed_definition_for_url,
    get_feed_definition,
    list_default_feeds,
)
from lib.live_feeds import fetch_rss_feed


def test_feed_registry_schema_and_json_serializable():
    feeds = build_feed_registry()
    assert feeds
    assert all(set(FEED_REGISTRY_SCHEMA).issubset(feed) for feed in feeds)
    json.dumps(feeds)

    default_feeds = list_default_feeds()
    assert default_feeds
    assert all(feed["default_enabled"] and not feed["requires_key"] for feed in default_feeds)
    assert {"rss", "json_api", "geojson_api", "static_registry"}.intersection({feed["source_type"] for feed in default_feeds})


def test_default_rss_feeds_are_registry_backed():
    urls = default_rss_feed_urls()
    assert "https://www.eia.gov/rss/todayinenergy.xml" in urls
    assert all(feed_definition_for_url(url) for url in urls)

    rows, status = fetch_rss_feed(parser=lambda url: [{"title": url, "url": url, "source": url}])
    assert status.ok
    assert len(rows) == len(urls)


def test_sanctions_and_optional_tracking_are_registry_only_or_missing_key():
    sanctions = get_feed_definition("sanctions.opensanctions_registry_only")
    ais = get_feed_definition("ais.aisstream_optional")
    flight = get_feed_definition("flight.opensky_optional")

    assert sanctions is not None
    assert sanctions["default_enabled"] is False
    assert sanctions["source_type"] == "registry_only"
    assert "no sanctions rows" in sanctions["caveat"].lower()

    assert ais and ais["requires_key"] is True
    assert flight and flight["requires_key"] is True
