from __future__ import annotations

import pandas as pd

from .data_status import ok_result


def get_macro_dashboard() -> tuple[pd.DataFrame, object]:
    data = pd.DataFrame(
        [
            {"module": "Rates", "status": "available via yfinance proxy"},
            {"module": "Dollar", "status": "available via yfinance proxy"},
            {"module": "FRED", "status": "optional key"},
        ]
    )
    return data, ok_result(data, source="macro module registry", provider="macro")


def build_unified_macro_dashboard(source_mode: str = "auto") -> dict:
    from .macro_regime_engine import build_macro_regime_cards
    from .openbb_macro_backend import build_macro_rates_dashboard_payload

    payload = build_macro_rates_dashboard_payload(source_mode=source_mode)
    payload["regime_cards"] = build_macro_regime_cards(payload)
    return payload
