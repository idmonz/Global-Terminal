from __future__ import annotations

from lib.portfolio_state import (
    cash_weight,
    default_portfolio_rows,
    list_saved_portfolios,
    load_portfolio_from_json,
    normalize_portfolio_rows,
    portfolio_rows_to_weights,
    portfolio_summary,
    save_portfolio_to_json,
    validate_portfolio_rows,
)


def test_portfolio_rows_normalize_and_persist(tmp_path):
    rows = normalize_portfolio_rows(default_portfolio_rows())
    ok, issues = validate_portfolio_rows(rows)
    weights = portfolio_rows_to_weights(rows)

    assert ok
    assert round(sum(weights.values()), 8) == 1
    assert cash_weight(rows) > 0
    assert portfolio_summary(rows)["asset_count"] >= 4

    path = tmp_path / "portfolio.json"
    save_portfolio_to_json("My Research Portfolio", rows, path)
    assert "My Research Portfolio" in list_saved_portfolios(path)
    loaded = load_portfolio_from_json("My Research Portfolio", path)
    assert loaded["ticker"].tolist() == rows["ticker"].tolist()
