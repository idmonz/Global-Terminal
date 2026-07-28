from __future__ import annotations


SECTOR_ETFS = [
    {"ticker": "XLK", "name": "Technology", "sector": "Information Technology"},
    {"ticker": "XLF", "name": "Financials", "sector": "Financials"},
    {"ticker": "XLV", "name": "Health Care", "sector": "Health Care"},
    {"ticker": "XLE", "name": "Energy", "sector": "Energy"},
    {"ticker": "XLI", "name": "Industrials", "sector": "Industrials"},
    {"ticker": "XLY", "name": "Consumer Discretionary", "sector": "Consumer Discretionary"},
    {"ticker": "XLP", "name": "Consumer Staples", "sector": "Consumer Staples"},
    {"ticker": "XLU", "name": "Utilities", "sector": "Utilities"},
    {"ticker": "XLRE", "name": "Real Estate", "sector": "Real Estate"},
    {"ticker": "XLB", "name": "Materials", "sector": "Materials"},
    {"ticker": "XLC", "name": "Communication Services", "sector": "Communication Services"},
]


G7_MARKETS = [
    {"country": "United States", "index": "^GSPC", "etf": "SPY", "currency": "USD", "fx": "DX-Y.NYB", "yield_10y": "^TNX"},
    {"country": "Japan", "index": "^N225", "etf": "EWJ", "currency": "JPY", "fx": "JPY=X", "yield_10y": None},
    {"country": "Germany", "index": "^GDAXI", "etf": "EWG", "currency": "EUR", "fx": "EURUSD=X", "yield_10y": None},
    {"country": "France", "index": "^FCHI", "etf": "EWQ", "currency": "EUR", "fx": "EURUSD=X", "yield_10y": None},
    {"country": "United Kingdom", "index": "^FTSE", "etf": "EWU", "currency": "GBP", "fx": "GBPUSD=X", "yield_10y": None},
    {"country": "Canada", "index": "^GSPTSE", "etf": "EWC", "currency": "CAD", "fx": "CAD=X", "yield_10y": None},
    {"country": "Italy", "index": "FTSEMIB.MI", "etf": "EWI", "currency": "EUR", "fx": "EURUSD=X", "yield_10y": None},
    {"country": "Korea", "index": "^KS11", "etf": "EWY", "currency": "KRW", "fx": "KRW=X", "yield_10y": None},
]


CROSS_ASSET_TICKERS = [
    {"ticker": "^GSPC", "name": "S&P 500", "asset_class": "Equities"},
    {"ticker": "^NDX", "name": "Nasdaq 100", "asset_class": "Equities"},
    {"ticker": "^DJI", "name": "Dow Jones", "asset_class": "Equities"},
    {"ticker": "^RUT", "name": "Russell 2000", "asset_class": "Equities"},
    {"ticker": "^N225", "name": "Nikkei 225", "asset_class": "Equities"},
    {"ticker": "^GDAXI", "name": "DAX", "asset_class": "Equities"},
    {"ticker": "^FCHI", "name": "CAC 40", "asset_class": "Equities"},
    {"ticker": "^FTSE", "name": "FTSE 100", "asset_class": "Equities"},
    {"ticker": "^GSPTSE", "name": "TSX", "asset_class": "Equities"},
    {"ticker": "FTSEMIB.MI", "name": "FTSE MIB", "asset_class": "Equities"},
    {"ticker": "^KS11", "name": "KOSPI", "asset_class": "Equities"},
    {"ticker": "^VIX", "name": "VIX", "asset_class": "Volatility"},
    {"ticker": "^TNX", "name": "US 10Y Yield", "asset_class": "Rates"},
    {"ticker": "DX-Y.NYB", "name": "US Dollar Index", "asset_class": "FX"},
    {"ticker": "GC=F", "name": "Gold", "asset_class": "Commodities"},
    {"ticker": "CL=F", "name": "WTI Crude", "asset_class": "Commodities"},
    {"ticker": "BZ=F", "name": "Brent Crude", "asset_class": "Commodities"},
    {"ticker": "BTC-USD", "name": "Bitcoin", "asset_class": "Crypto"},
    {"ticker": "ETH-USD", "name": "Ethereum", "asset_class": "Crypto"},
]


CRYPTO_MARKETS = [
    {"ticker": "BTC-USD", "name": "Bitcoin", "category": "Major"},
    {"ticker": "ETH-USD", "name": "Ethereum", "category": "Major"},
    {"ticker": "SOL-USD", "name": "Solana", "category": "Layer 1"},
    {"ticker": "BNB-USD", "name": "BNB", "category": "Exchange"},
    {"ticker": "XRP-USD", "name": "XRP", "category": "Payments"},
    {"ticker": "ADA-USD", "name": "Cardano", "category": "Layer 1"},
    {"ticker": "DOGE-USD", "name": "Dogecoin", "category": "Meme"},
]


def list_global_market_proxies() -> dict:
    return {
        "g7": G7_MARKETS,
        "cross_asset": CROSS_ASSET_TICKERS,
        "sectors": SECTOR_ETFS,
        "crypto": CRYPTO_MARKETS,
    }
