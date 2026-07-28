from lib.watchlist_store import create_watchlist_item
from lib.watchlist_engine import build_watchlist_context, build_watchlist_heatmap_payload, build_watchlist_rmi_payload, build_watchlist_volatility_payload


def test_watchlist_asset_enriched_with_supplied_market_context(tmp_path):
    db = tmp_path / "research.db"
    create_watchlist_item(item_type="asset", symbol="AAPL", display_name="Apple", asset_class="equity", db_path=db)
    context = {"market": {"AAPL": {"latest_value": 210.5, "change_pct": 1.2, "realized_volatility_pct": 24.0, "freshness": "fresh", "data_confidence": "high", "source": "mock-udl"}}}
    payload = build_watchlist_context(db, supplied_context=context)
    row = payload["table"][0]
    assert row["latest_value"] == 210.5
    assert row["freshness"] == "fresh"
    assert row["data_confidence"] == "high"
    heatmap = build_watchlist_heatmap_payload(db, supplied_context=context)
    assert heatmap.get("tiles") or heatmap.get("rows") or heatmap.get("layout") is not None
    assert build_watchlist_rmi_payload(db, supplied_context=context)["market_rows_used"] == 1
    assert build_watchlist_volatility_payload(db, supplied_context=context)["market_rows_used"] == 1


def test_watchlist_region_and_provider_context(tmp_path):
    db = tmp_path / "research.db"
    create_watchlist_item(item_type="chokepoint", display_name="Red Sea", region="Middle East", tags=["energy"], db_path=db)
    create_watchlist_item(item_type="provider", symbol="FRED", display_name="Provider: FRED", db_path=db)
    supplied = {"events": [{"title": "Bab el-Mandeb shipping disruption", "summary": "Energy cargo delays", "source": "mock-news", "freshness": "fresh", "severity": 8}], "providers": {"fred": {"provider_name": "FRED", "status": "missing_key", "freshness": "missing-key", "confidence": "low", "missing_keys": ["FRED_API_KEY"]}}}
    payload = build_watchlist_context(db, supplied_context=supplied)
    assert payload["bundle"]["events"]["match_count"] >= 1
    provider_rows = [r for r in payload["enriched_items"] if r["item_type"] == "provider"]
    assert provider_rows[0]["source_status"] == "missing_key"
