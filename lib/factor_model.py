from __future__ import annotations

import pandas as pd


def simple_factor_exposure_proxy(tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"ticker": tickers, "equity_beta_proxy": [1.0 for _ in tickers], "rate_sensitivity_proxy": [0.0 for _ in tickers]})

