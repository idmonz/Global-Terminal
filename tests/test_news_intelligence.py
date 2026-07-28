from __future__ import annotations

from datetime import datetime, timezone

from lib.news_intelligence import (
    build_high_severity_feed,
    build_market_impact_matrix,
    build_news_timeline,
    build_regional_news_cards,
    build_source_freshness_panel,
    build_worldmonitor_style_news_dashboard,
    classify_news_asset_tags,
    classify_news_credibility,
    classify_news_region,
    classify_news_severity,
    extract_related_assets,
    normalize_news_item,
)
from lib.data_status import error_result, ok_result


SAMPLE_NEWS = [
    {
        "title": "Oil tankers reroute after missile attack near Strait of Hormuz",
        "summary": "Brent and WTI traders monitor shipping risk in the Persian Gulf.",
        "source": "reuters.com",
        "published_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "Fed rate decision lifts Treasury yield volatility",
        "summary": "Macro desks track rates and dollar channels.",
        "source": "federalreserve.gov",
        "published_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "Bitcoin exchange security incident raises crypto risk watch",
        "summary": "BTC and ETH liquidity conditions remain under review.",
        "source": "example.com",
        "published_at": datetime.now(timezone.utc).isoformat(),
    },
]


def test_news_item_normalization_and_classifiers():
    item = normalize_news_item(SAMPLE_NEWS[0])
    assert item["severity"] == "high"
    assert item["region"] == "Middle East"
    assert "oil" in item["impact_channels"]
    assert "shipping" in item["impact_channels"]
    assert "WTI" in item["related_assets"]
    assert item["classification_method"] == "heuristic"
    assert classify_news_severity(SAMPLE_NEWS[0]) == "high"
    assert classify_news_region(SAMPLE_NEWS[0]) == "Middle East"
    assert "oil" in classify_news_asset_tags(SAMPLE_NEWS[0])
    assert classify_news_credibility(SAMPLE_NEWS[1]) == "official"
    assert "BTC" in extract_related_assets(SAMPLE_NEWS[2])


def test_news_item_region_centroid_for_unmapped_public_feed():
    item = normalize_news_item(
        {
            "title": "U.S. jet fuel production rises after prices drop",
            "summary": "Official EIA energy update.",
            "source": "https://www.eia.gov/rss/todayinenergy.xml",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    assert item["region"] == "Americas"
    assert item["lat"] is not None
    assert item["lon"] is not None
    assert item["coordinate_method"] == "region_centroid"


def test_news_dashboard_schemas():
    timeline = build_news_timeline(SAMPLE_NEWS)
    matrix = build_market_impact_matrix(SAMPLE_NEWS)
    high = build_high_severity_feed(SAMPLE_NEWS)
    regional = build_regional_news_cards(SAMPLE_NEWS)
    freshness = build_source_freshness_panel(SAMPLE_NEWS)
    dashboard = build_worldmonitor_style_news_dashboard(SAMPLE_NEWS)

    assert {"period", "total_count", "high_count"}.issubset(timeline.columns)
    assert {"impact_channel", "total_count", "high_count", "top_related_assets"}.issubset(matrix.columns)
    assert not high.empty
    assert {"region", "score", "method"}.issubset(regional.columns)
    assert {"source", "status", "feed_count"}.issubset(freshness.columns)
    assert {"normalized_news", "impact_matrix", "source_freshness", "event_rows"}.issubset(dashboard)
    assert dashboard["source_status_summary"]["status"] == "available"


def test_worldmonitor_style_news_dashboard_provenance_and_empty_state():
    row = {
        "title": "USGS reports earthquake near coast",
        "summary": "Official alert.",
        "source": "USGS",
        "source_url": "https://earthquake.usgs.gov/event/test",
        "provider": "usgs_earthquake",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "published_at": datetime.now(timezone.utc).isoformat(),
        "freshness": "fresh",
        "source_status": "fresh",
        "confidence": 0.95,
        "lat": 1.0,
        "lon": 2.0,
        "coordinate_method": "usgs_geojson",
    }
    dashboard = build_worldmonitor_style_news_dashboard([row], [ok_result([], source="USGS", provider="usgs_earthquake")])
    normalized = dashboard["normalized_news"].iloc[0]

    assert dashboard["source_status_summary"]["status"] == "available"
    assert normalized["provider"] == "usgs_earthquake"
    assert normalized["source_url"].startswith("https://")
    assert normalized["coordinate_method"] == "usgs_geojson"

    empty = build_worldmonitor_style_news_dashboard([], [error_result(source="GDELT", provider="gdelt", error="timeout")])
    assert empty["source_status_summary"]["status"] == "unavailable"
    assert empty["source_status_summary"]["error_count"] == 1
    assert "No public feed rows are available" in empty["notes"][0]
