from __future__ import annotations


def get_etf_peer_group(ticker: str) -> list[str]:
    ticker = ticker.upper()
    if ticker in {"SPY", "IVV", "VOO"}:
        return ["SPY", "IVV", "VOO"]
    if ticker in {"QQQ", "QQQM"}:
        return ["QQQ", "QQQM"]
    return [ticker]

