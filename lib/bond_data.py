from __future__ import annotations

from .data_status import failure, success
from .market_data import fetch_multi_history

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


BOND_RATE_PROXIES = [
    {"ticker": "BIL", "name": "1-3 Month T-Bill ETF", "duration_bucket": "cash / bills", "rate_sensitivity": "very low"},
    {"ticker": "SHY", "name": "1-3 Year Treasury ETF", "duration_bucket": "short", "rate_sensitivity": "low"},
    {"ticker": "IEI", "name": "3-7 Year Treasury ETF", "duration_bucket": "intermediate", "rate_sensitivity": "medium"},
    {"ticker": "IEF", "name": "7-10 Year Treasury ETF", "duration_bucket": "intermediate-long", "rate_sensitivity": "medium-high"},
    {"ticker": "TLT", "name": "20+ Year Treasury ETF", "duration_bucket": "long", "rate_sensitivity": "high"},
    {"ticker": "TIP", "name": "TIPS ETF", "duration_bucket": "inflation-linked", "rate_sensitivity": "medium"},
    {"ticker": "LQD", "name": "Investment Grade Credit ETF", "duration_bucket": "credit", "rate_sensitivity": "medium"},
    {"ticker": "HYG", "name": "High Yield Credit ETF", "duration_bucket": "credit", "rate_sensitivity": "lower duration / credit spread"},
]


def build_bond_proxy_universe():
    if pd is None:
        return [], failure(source="bond proxy universe", provider="static", error="pandas is not installed")
    frame = pd.DataFrame(BOND_RATE_PROXIES)
    return frame, success(frame, source="bond proxy universe", provider="static", is_estimated=True, coverage=f"{len(frame)} proxies")


def build_bond_proxy_metrics(period: str = "1y"):
    if pd is None:
        return [], failure(source="bond proxy metrics", provider="yfinance", error="pandas is not installed")
    universe, universe_status = build_bond_proxy_universe()
    tickers = universe["ticker"].tolist()
    history, history_status = fetch_multi_history(tickers, period=period)
    rows = []
    for item in BOND_RATE_PROXIES:
        ticker = item["ticker"]
        close = None
        if history is not None and not getattr(history, "empty", True):
            try:
                if isinstance(history.columns, pd.MultiIndex) and ticker in history.columns.get_level_values(0):
                    frame = history[ticker]
                else:
                    frame = history
                close_col = "Adj Close" if "Adj Close" in frame.columns else "Close"
                close = frame[close_col].dropna()
            except Exception:
                close = None
        row = dict(item)
        if close is not None and len(close) > 1:
            returns = close.pct_change().dropna()
            row.update(
                {
                    "price": float(close.iloc[-1]),
                    "return_period_pct": float((close.iloc[-1] / close.iloc[0] - 1) * 100),
                    "volatility_pct": float(returns.std() * (252**0.5) * 100) if not returns.empty else None,
                    "drawdown_pct": float((close.iloc[-1] / close.cummax().iloc[-1] - 1) * 100),
                    "yield_proxy": "ETF distribution/yield data unavailable in free mode",
                    "data_status": "real/delayed yfinance",
                }
            )
        else:
            row.update(
                {
                    "price": None,
                    "return_period_pct": None,
                    "volatility_pct": None,
                    "drawdown_pct": None,
                    "yield_proxy": "data gap",
                    "data_status": "price data unavailable",
                }
            )
        rows.append(row)
    frame = pd.DataFrame(rows)
    status = history_status if history_status is not None else universe_status
    return frame, status
