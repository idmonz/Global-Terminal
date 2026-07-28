from lib.heatmaps import load_static_constituents
from lib.ui import unique_existing_columns


def test_static_sp500_seed_loads():
    data, status = load_static_constituents("sp500")
    assert status.ok
    assert len(data) >= 20
    assert {"ticker", "company", "sector", "name", "group"}.issubset(data.columns)
    assert data["name"].notna().all()


def test_static_korea_seed_loads():
    data, status = load_static_constituents("korea_watchlist")
    assert status.ok
    assert len(data) >= 10
    assert {"ticker", "name", "group"}.issubset(data.columns)


def test_heatmap_table_columns_are_unique_for_all_metrics():
    for metric_col in ["daily_return", "weekly_return", "monthly_return", "ytd_return"]:
        candidate_cols = ["ticker", "name", "company", "sector", "price", metric_col, "daily_return", "weekly_return", "monthly_return", "ytd_return", "regime", "data_quality"]
        cols = unique_existing_columns(candidate_cols, ["ticker", "name", "sector", metric_col])
        assert len(cols) == len(set(cols))
