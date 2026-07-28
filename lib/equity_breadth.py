from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from .config import INDEX_CONSTITUENTS_DIR
from .data_status import error_result, ok_result
from .market_data import fetch_many_price_histories


REQUIRED_UNIVERSE_COLUMNS = {"ticker", "company", "sector"}


def _fallback_universe(name: str) -> pd.DataFrame:
    rows = {
        "sp500": [
            {"ticker": "AAPL", "company": "Apple", "sector": "Technology", "industry": "Consumer Electronics", "market_cap": 3000},
            {"ticker": "MSFT", "company": "Microsoft", "sector": "Technology", "industry": "Software", "market_cap": 3200},
            {"ticker": "JPM", "company": "JPMorgan Chase", "sector": "Financials", "industry": "Banks", "market_cap": 550},
            {"ticker": "XOM", "company": "Exxon Mobil", "sector": "Energy", "industry": "Integrated Oil", "market_cap": 500},
        ],
        "nasdaq100": [
            {"ticker": "AAPL", "company": "Apple", "sector": "Technology", "industry": "Consumer Electronics", "market_cap": 3000},
            {"ticker": "MSFT", "company": "Microsoft", "sector": "Technology", "industry": "Software", "market_cap": 3200},
            {"ticker": "NVDA", "company": "NVIDIA", "sector": "Technology", "industry": "Semiconductors", "market_cap": 2800},
            {"ticker": "AMZN", "company": "Amazon", "sector": "Consumer Discretionary", "industry": "Internet Retail", "market_cap": 1800},
        ],
        "korea": [
            {"ticker": "005930.KS", "company": "Samsung Electronics", "sector": "Technology", "industry": "Semiconductors", "market_cap": 1},
            {"ticker": "000660.KS", "company": "SK Hynix", "sector": "Technology", "industry": "Semiconductors", "market_cap": 1},
        ],
    }
    return pd.DataFrame(rows.get(name, rows["sp500"]))


def _read_universe(filename: str, fallback_name: str) -> pd.DataFrame:
    path = INDEX_CONSTITUENTS_DIR / filename
    if path.exists():
        return pd.read_csv(path)
    return _fallback_universe(fallback_name)


def validate_universe_schema(universe: pd.DataFrame) -> tuple[bool, list[str]]:
    if universe is None or universe.empty:
        return False, ["universe is empty"]
    missing = sorted(REQUIRED_UNIVERSE_COLUMNS - set(universe.columns))
    return not missing, missing


def load_sp500_universe() -> tuple[pd.DataFrame, object]:
    data = _read_universe("sp500.csv", "sp500")
    valid, missing = validate_universe_schema(data)
    if not valid:
        return data, error_result(source="static/index_constituents/sp500.csv", provider="equity_universe", error=f"Missing columns: {missing}")
    return data, ok_result(data, source="static/index_constituents/sp500.csv", provider="equity_universe", coverage=f"{len(data)} symbols")


def load_nasdaq100_universe() -> tuple[pd.DataFrame, object]:
    data = _read_universe("nasdaq100.csv", "nasdaq100")
    valid, missing = validate_universe_schema(data)
    if not valid:
        return data, error_result(source="static/index_constituents/nasdaq100.csv", provider="equity_universe", error=f"Missing columns: {missing}")
    return data, ok_result(data, source="static/index_constituents/nasdaq100.csv", provider="equity_universe", coverage=f"{len(data)} symbols")


def load_sector_universe() -> tuple[pd.DataFrame, object]:
    data = pd.DataFrame(
        [
            {"ticker": "XLK", "company": "Technology Select Sector SPDR", "sector": "Technology", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLF", "company": "Financial Select Sector SPDR", "sector": "Financials", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLV", "company": "Health Care Select Sector SPDR", "sector": "Health Care", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLE", "company": "Energy Select Sector SPDR", "sector": "Energy", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLI", "company": "Industrial Select Sector SPDR", "sector": "Industrials", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLY", "company": "Consumer Discretionary Select Sector SPDR", "sector": "Consumer Discretionary", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLP", "company": "Consumer Staples Select Sector SPDR", "sector": "Consumer Staples", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLU", "company": "Utilities Select Sector SPDR", "sector": "Utilities", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLRE", "company": "Real Estate Select Sector SPDR", "sector": "Real Estate", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLB", "company": "Materials Select Sector SPDR", "sector": "Materials", "industry": "Sector ETF", "market_cap": 1},
            {"ticker": "XLC", "company": "Communication Services Select Sector SPDR", "sector": "Communication Services", "industry": "Sector ETF", "market_cap": 1},
        ]
    )
    return data, ok_result(data, source="sector ETF registry", provider="equity_universe", coverage=f"{len(data)} symbols")


def load_korea_universe_if_available() -> tuple[pd.DataFrame, object]:
    data = _read_universe("korea_watchlist.csv", "korea")
    valid, missing = validate_universe_schema(data)
    if not valid:
        return data, error_result(source="static/index_constituents/korea_watchlist.csv", provider="equity_universe", error=f"Missing columns: {missing}")
    return data, ok_result(data, source="static/index_constituents/korea_watchlist.csv", provider="equity_universe", coverage=f"{len(data)} symbols")


def _close(frame: pd.DataFrame) -> pd.Series:
    if frame is None or frame.empty:
        return pd.Series(dtype=float)
    col = "close" if "close" in frame.columns else "Close" if "Close" in frame.columns else None
    if col is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[col], errors="coerce").dropna()


def _iter_valid_histories(histories: Mapping[str, pd.DataFrame]):
    for symbol, frame in histories.items():
        close = _close(frame)
        if len(close) >= 2:
            yield symbol, close


def compute_above_moving_average_percent(histories: Mapping[str, pd.DataFrame], window: int = 50) -> float:
    flags = []
    for _, close in _iter_valid_histories(histories):
        if len(close) >= window:
            ma = close.rolling(window).mean().iloc[-1]
            flags.append(float(close.iloc[-1] > ma))
    if not flags:
        return float("nan")
    return float(np.mean(flags) * 100)


def compute_advance_decline_ratio(histories: Mapping[str, pd.DataFrame]) -> float:
    advances = 0
    declines = 0
    for _, close in _iter_valid_histories(histories):
        change = close.iloc[-1] - close.iloc[-2]
        if change > 0:
            advances += 1
        elif change < 0:
            declines += 1
    if declines == 0:
        return float(advances) if advances else float("nan")
    return float(advances / declines)


def compute_new_high_new_low_proxy(histories: Mapping[str, pd.DataFrame], window: int = 252) -> tuple[int, int]:
    highs = 0
    lows = 0
    for _, close in _iter_valid_histories(histories):
        lookback = close.tail(min(window, len(close)))
        if lookback.empty:
            continue
        highs += int(close.iloc[-1] >= lookback.max())
        lows += int(close.iloc[-1] <= lookback.min())
    return highs, lows


def compute_equal_weight_vs_cap_weight_proxy(histories: Mapping[str, pd.DataFrame], universe: pd.DataFrame | None = None) -> float:
    returns: list[tuple[str, float]] = []
    for symbol, close in _iter_valid_histories(histories):
        returns.append((symbol, float(close.iloc[-1] / close.iloc[-2] - 1)))
    if not returns:
        return float("nan")
    equal_weight = float(np.mean([value for _, value in returns]))
    if universe is None or "market_cap" not in universe.columns:
        return equal_weight
    weights = universe.set_index("ticker")["market_cap"].reindex([symbol for symbol, _ in returns]).fillna(1).astype(float)
    weights = weights / weights.sum() if weights.sum() else weights
    cap_weight = float(np.dot(weights.to_numpy(), np.array([value for _, value in returns])))
    return float(equal_weight - cap_weight)


def compute_sector_participation(universe: pd.DataFrame, histories: Mapping[str, pd.DataFrame], window: int = 50) -> float:
    if universe is None or universe.empty or "sector" not in universe.columns:
        return float("nan")
    sector_scores = []
    for _, group in universe.groupby("sector"):
        subset = {ticker: histories[ticker] for ticker in group["ticker"] if ticker in histories}
        pct = compute_above_moving_average_percent(subset, window=window)
        if pd.notna(pct):
            sector_scores.append(pct / 100)
    if not sector_scores:
        return float("nan")
    return float(np.mean(sector_scores) * 100)


def compute_breadth_thrust_proxy(histories: Mapping[str, pd.DataFrame]) -> float:
    adv_dec = compute_advance_decline_ratio(histories)
    above_20 = compute_above_moving_average_percent(histories, window=20)
    if pd.isna(adv_dec) or pd.isna(above_20):
        return float("nan")
    return float(min(100, above_20 * (adv_dec / (adv_dec + 1))))


def compute_breadth_regime(snapshot: dict) -> str:
    above_50 = snapshot.get("above_50dma_pct")
    above_200 = snapshot.get("above_200dma_pct")
    adv_dec = snapshot.get("advance_decline_ratio")
    if pd.isna(above_50) or pd.isna(above_200):
        return "Data gap"
    if above_50 >= 65 and above_200 >= 55 and (pd.isna(adv_dec) or adv_dec >= 1):
        return "Breadth expansion"
    if above_50 <= 35 or above_200 <= 35:
        return "Breadth deterioration"
    return "Neutral / mixed evidence"


def build_breadth_snapshot(universe: pd.DataFrame, histories: Mapping[str, pd.DataFrame], universe_name: str) -> dict:
    new_highs, new_lows = compute_new_high_new_low_proxy(histories)
    snapshot = {
        "universe": universe_name,
        "timestamp": pd.Timestamp.utcnow().isoformat(),
        "symbols_total": int(len(universe)),
        "symbols_valid": int(sum(1 for _ in _iter_valid_histories(histories))),
        "above_20dma_pct": compute_above_moving_average_percent(histories, window=20),
        "above_50dma_pct": compute_above_moving_average_percent(histories, window=50),
        "above_100dma_pct": compute_above_moving_average_percent(histories, window=100),
        "above_200dma_pct": compute_above_moving_average_percent(histories, window=200),
        "advance_decline_ratio": compute_advance_decline_ratio(histories),
        "new_highs_proxy": int(new_highs),
        "new_lows_proxy": int(new_lows),
        "equal_weight_relative_strength": compute_equal_weight_vs_cap_weight_proxy(histories, universe),
        "sector_participation_score": compute_sector_participation(universe, histories, window=50),
        "data_gaps": [],
    }
    if snapshot["symbols_valid"] < snapshot["symbols_total"]:
        snapshot["data_gaps"].append(f"{snapshot['symbols_total'] - snapshot['symbols_valid']} symbols missing or insufficient history")
    snapshot["breadth_regime"] = compute_breadth_regime(snapshot)
    return snapshot


def compute_index_breadth_snapshot(universe: str = "sp500", histories: Mapping[str, pd.DataFrame] | None = None) -> tuple[dict, object]:
    loaders = {
        "sp500": load_sp500_universe,
        "nasdaq100": load_nasdaq100_universe,
        "sector": load_sector_universe,
        "korea": load_korea_universe_if_available,
    }
    loader = loaders.get(universe, load_sp500_universe)
    universe_df, universe_status = loader()
    if histories is None:
        histories, price_status = fetch_many_price_histories(universe_df["ticker"].dropna().astype(str).head(80), period="1y")
    else:
        price_status = ok_result(histories, source="provided histories", provider="equity_breadth", coverage=f"{len(histories)} symbols")
    snapshot = build_breadth_snapshot(universe_df, histories, universe)
    if snapshot["symbols_valid"] == 0:
        return snapshot, error_result(source="equity breadth", provider="equity_breadth", error="No valid symbols for breadth snapshot.", warning=price_status.error)
    warning = "; ".join(snapshot["data_gaps"]) if snapshot["data_gaps"] else price_status.warning
    return snapshot, ok_result(snapshot, source="equity breadth", provider="equity_breadth", warning=warning, coverage=f"{snapshot['symbols_valid']}/{snapshot['symbols_total']} symbols")

