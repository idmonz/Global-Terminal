from lib.options_book_risk import aggregate_by_expiry, aggregate_by_moneyness_bucket, aggregate_by_underlying, build_option_book_risk_snapshot

POSITIONS=[{"position_id":"p1","underlying":"DEMO","option_type":"call","expiry":"2026-12-31","strike":100,"quantity":1,"position":"long","premium":5,"mark":6,"implied_volatility":0.2,"underlying_price":100}, {"position_id":"p2","underlying":"DEMO","option_type":"put","expiry":"2027-03-31","strike":95,"quantity":1,"position":"short","premium":3,"mark":2,"implied_volatility":0.25,"underlying_price":100}]

def test_option_book_risk_aggregates_contract_scaled_units():
    snap=build_option_book_risk_snapshot(POSITIONS)
    assert snap["ok"] is True
    assert "total_delta" in snap["totals"]
    assert len(aggregate_by_underlying(snap["positions"])) == 1
    assert len(aggregate_by_expiry(snap["positions"])) == 2
    assert aggregate_by_moneyness_bucket(snap["positions"])
