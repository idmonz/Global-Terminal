from __future__ import annotations

import numpy as np
import pandas as pd

from .portfolio_state import normalize_portfolio_rows, portfolio_summary


def parse_weights(tickers: list[str], weights_text: str | None = None) -> list[float]:
    if not tickers:
        return []
    if not weights_text:
        return [1 / len(tickers)] * len(tickers)
    values = [float(item.strip()) for item in weights_text.split(",") if item.strip()]
    if len(values) != len(tickers) or sum(values) == 0:
        return [1 / len(tickers)] * len(tickers)
    values = np.array(values, dtype=float)
    values = values / values.sum()
    return values.tolist()


def holdings_frame(tickers: list[str], weights: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"ticker": tickers, "weight": weights})


def holdings_summary(rows) -> dict:
    return portfolio_summary(normalize_portfolio_rows(rows))
