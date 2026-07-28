from __future__ import annotations


SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
    "Communication Services": "XLC",
}

G7_MARKETS = {
    "United States": {"index": "^GSPC", "etf": "SPY", "currency": "USD"},
    "Japan": {"index": "^N225", "etf": "EWJ", "currency": "JPY=X"},
    "Germany": {"index": "^GDAXI", "etf": "EWG", "currency": "EURUSD=X"},
    "France": {"index": "^FCHI", "etf": "EWQ", "currency": "EURUSD=X"},
    "United Kingdom": {"index": "^FTSE", "etf": "EWU", "currency": "GBPUSD=X"},
    "Canada": {"index": "^GSPTSE", "etf": "EWC", "currency": "CAD=X"},
    "Italy": {"index": "FTSEMIB.MI", "etf": "EWI", "currency": "EURUSD=X"},
    "Korea": {"index": "^KS11", "etf": "EWY", "currency": "KRW=X"},
}

CROSS_ASSET_TICKERS = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "Dow Jones": "^DJI",
    "Russell 2000": "^RUT",
    "Volatility": "^VIX",
    "US 10Y": "^TNX",
    "Gold": "GC=F",
    "WTI Crude": "CL=F",
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "US Dollar": "DX-Y.NYB",
    "Nikkei": "^N225",
    "DAX": "^GDAXI",
    "CAC": "^FCHI",
    "FTSE": "^FTSE",
    "TSX": "^GSPTSE",
    "KOSPI": "^KS11",
}

