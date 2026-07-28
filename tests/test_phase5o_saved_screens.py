from __future__ import annotations

import json

import pytest

from lib.saved_market_screens import (
    archive_market_screen,
    build_saved_screen_readiness,
    list_market_screens,
    rename_market_screen,
    save_market_screen,
)
from lib.research_workspace_migrations import get_workspace_schema_version, run_workspace_migrations
from lib.research_workspace_schema import SCHEMA_VERSION


DEFINITION = {
    "universe": "bounded-us-largecap",
    "sectors": ["Technology"],
    "market_cap": "mega",
    "return_1d": "all",
    "return_1m": "positive",
    "volatility": "moderate",
    "rsi": "constructive",
    "trend": "above-sma20",
    "valuation": "available",
    "quality": "complete",
    "rank": "balanced",
    "display": "heatmap",
}


def test_schema_v5_and_saved_screen_crud(tmp_path):
    db = tmp_path / "screens.db"
    run_workspace_migrations(db)
    assert get_workspace_schema_version(db) == SCHEMA_VERSION
    assert SCHEMA_VERSION >= 7

    saved = save_market_screen("Daily quality", DEFINITION, db_path=db)
    assert saved["privacy_scope"] == "local-private"
    assert saved["definition"]["rank"] == "balanced"
    assert [row["screen_id"] for row in list_market_screens(db_path=db)] == [saved["screen_id"]]

    renamed = rename_market_screen(saved["screen_id"], "Morning discovery", db_path=db)
    assert renamed["name"] == "Morning discovery"
    assert archive_market_screen(saved["screen_id"], db_path=db) is True
    assert list_market_screens(db_path=db) == []


def test_saved_screen_validation_blocks_private_or_unbounded_state(tmp_path):
    db = tmp_path / "invalid.db"
    with pytest.raises(ValueError):
        save_market_screen("../private", DEFINITION, db_path=db)
    with pytest.raises(ValueError):
        save_market_screen("Bad filter", {**DEFINITION, "rank": "unknown-model"}, db_path=db)
    with pytest.raises(ValueError):
        save_market_screen("Private symbol", {**DEFINITION, "symbol": "SECRET"}, db_path=db)


def test_saved_screen_readiness_and_serialization_do_not_expose_path(tmp_path):
    db = tmp_path / "ready.db"
    readiness = build_saved_screen_readiness(db_path=db)
    encoded = json.dumps(readiness)

    assert readiness["store_status"] == "ready"
    assert readiness["privacy_scope"] == "local-private"
    assert str(tmp_path) not in encoded
    assert "ready.db" not in encoded
