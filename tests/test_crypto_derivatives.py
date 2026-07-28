from lib.crypto_derivatives import (
    FUNDING_COLUMNS,
    KLINE_COLUMNS,
    OI_HISTORY_COLUMNS,
    RATIO_COLUMNS,
    TAKER_COLUMNS,
    get_binance_klines,
    get_funding_rate_history,
    get_global_long_short_ratio,
    get_open_interest_history,
    get_taker_buy_sell_ratio,
    normalize_symbol,
)
from lib.data_status import failure, success


def test_symbol_normalization():
    assert normalize_symbol("btcusdt") == "BTCUSDT"
    assert normalize_symbol("BTC/USDT") == "BTCUSDT"
    assert normalize_symbol("BTC-USDT") == "BTCUSDT"


def test_klines_schema(monkeypatch):
    payload = [[1710000000000, "100", "110", "90", "105", "10", 1710003599999, "1000", 20, "5", "500", "0"]]

    def fake_get(path, **kwargs):
        return payload, success(payload, source="unit", provider="binance")

    monkeypatch.setattr("lib.crypto_derivatives._binance_get", fake_get)
    frame, status = get_binance_klines("BTCUSDT", "1h", 1)
    assert status.ok
    assert list(frame.columns) == KLINE_COLUMNS
    assert frame["close"].iloc[0] == 105


def test_funding_oi_taker_and_ratio_schemas(monkeypatch):
    def fake_get(path, **kwargs):
        if "openInterestHist" in path:
            payload = [{"timestamp": 1710000000000, "sumOpenInterest": "10", "sumOpenInterestValue": "1000"}]
        elif "fundingRate" in path:
            payload = [{"fundingTime": 1710000000000, "fundingRate": "0.0001", "symbol": "BTCUSDT"}]
        elif "takerlongshortRatio" in path:
            payload = [{"timestamp": 1710000000000, "buySellRatio": "1.1", "buyVol": "11", "sellVol": "10"}]
        else:
            payload = [{"timestamp": 1710000000000, "longShortRatio": "1.2", "longAccount": "0.55", "shortAccount": "0.45"}]
        return payload, success(payload, source="unit", provider="binance")

    monkeypatch.setattr("lib.crypto_derivatives._binance_get", fake_get)
    oi, _ = get_open_interest_history("BTCUSDT")
    funding, _ = get_funding_rate_history("BTCUSDT")
    taker, _ = get_taker_buy_sell_ratio("BTCUSDT")
    ratio, _ = get_global_long_short_ratio("BTCUSDT")
    assert list(oi.columns) == OI_HISTORY_COLUMNS
    assert list(funding.columns) == FUNDING_COLUMNS
    assert list(taker.columns) == TAKER_COLUMNS
    assert list(ratio.columns) == RATIO_COLUMNS


def test_malformed_response_is_failure(monkeypatch):
    def fake_get(path, **kwargs):
        return {"bad": "shape"}, success({"bad": "shape"}, source="unit", provider="binance")

    monkeypatch.setattr("lib.crypto_derivatives._binance_get", fake_get)
    frame, status = get_open_interest_history("BTCUSDT")
    assert frame.empty
    assert not status.ok
    assert "not a list" in status.error


def test_rate_limit_style_failure(monkeypatch):
    def fake_get(path, **kwargs):
        return None, failure(source="unit", provider="binance", error="429 rate limited")

    monkeypatch.setattr("lib.crypto_derivatives._binance_get", fake_get)
    frame, status = get_taker_buy_sell_ratio("BTCUSDT")
    assert frame.empty
    assert not status.ok
    assert "429" in status.error
