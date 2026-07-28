from __future__ import annotations

from typing import Any

import pandas as pd


def build_regime_performance_table(strategy_returns: pd.DataFrame, regimes: Any | None = None) -> pd.DataFrame:
    if strategy_returns is None or strategy_returns.empty:
        return pd.DataFrame(columns=["regime", "strategy", "mean_return", "hit_rate", "observations", "source"])
    if regimes is None:
        regime_series = pd.Series("proxy_mixed", index=strategy_returns.index)
    elif isinstance(regimes, pd.Series):
        regime_series = regimes.reindex(strategy_returns.index).fillna("proxy_mixed")
    else:
        regime_series = pd.Series(regimes, index=strategy_returns.index).fillna("proxy_mixed")
    rows = []
    for regime, subset_index in regime_series.groupby(regime_series).groups.items():
        subset = strategy_returns.loc[subset_index]
        for column in subset.columns:
            series = subset[column].dropna()
            rows.append({"regime": regime, "strategy": column, "mean_return": float(series.mean()) if not series.empty else 0.0, "hit_rate": float((series > 0).mean()) if not series.empty else 0.0, "observations": int(series.count()), "source": "proxy regime"})
    return pd.DataFrame(rows)


def build_regime_performance_summary(table: pd.DataFrame) -> dict[str, Any]:
    return {"rows": int(len(table)), "regimes": sorted(table["regime"].dropna().unique().tolist()) if not table.empty else [], "caveat": "Regime labels may be proxy and should be validated."}
