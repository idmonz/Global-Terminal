from __future__ import annotations

import pandas as pd

from .data_status import ok_result


def get_rates_snapshot() -> tuple[pd.DataFrame, object]:
    data = pd.DataFrame([{"ticker": "^TNX", "label": "US 10Y proxy", "source_status": "yfinance proxy"}])
    return data, ok_result(data, source="static rates proxy", provider="rates", is_estimated=True)


def get_unified_rates_curve(source_mode: str = "auto"):
    from .openbb_macro_backend import get_treasury_curve_unified

    return get_treasury_curve_unified(source_mode=source_mode)
