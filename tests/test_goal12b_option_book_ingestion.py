from lib.options_book_ingestion import normalize_option_book_positions


def test_option_book_ingestion_accepts_local_positions_only():
    rows=[{"position_id":"p1","underlying":"DEMO","option_type":"C","expiry":"2026-12-31","strike":100,"quantity":2,"position":"long","premium":5,"mark":6,"implied_volatility":0.2,"underlying_price":100}]
    result=normalize_option_book_positions(rows)
    assert result["ok"] is True
    assert result["positions"][0]["option_type"] == "call"
    assert result["positions"][0]["source"] == "user_supplied_local_position"
