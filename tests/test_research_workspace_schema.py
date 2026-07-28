from lib.research_workspace_schema import TABLE_NAMES, get_schema_sql


def test_workspace_schema_tables_declared():
    assert "watchlist_items" in TABLE_NAMES
    assert "strategy_commits" in TABLE_NAMES
    assert len(get_schema_sql()) >= len(TABLE_NAMES)

