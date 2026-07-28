from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_router import request_macro_series, request_rates_curve


MACRO_SERIES = {
    "cpi": "CPIAUCSL",
    "pce": "PCEPI",
    "unemployment": "UNRATE",
    "gdp": "GDP",
}


def get_macro_series_unified(series_id: str, *, source_mode: str = "auto", **kwargs: Any):
    return request_macro_series(series_id, source_mode=source_mode, **kwargs)


def get_cpi_unified(*, source_mode: str = "auto", **kwargs: Any):
    return get_macro_series_unified(MACRO_SERIES["cpi"], source_mode=source_mode, **kwargs)


def get_pce_unified(*, source_mode: str = "auto", **kwargs: Any):
    return get_macro_series_unified(MACRO_SERIES["pce"], source_mode=source_mode, **kwargs)


def get_unemployment_unified(*, source_mode: str = "auto", **kwargs: Any):
    return get_macro_series_unified(MACRO_SERIES["unemployment"], source_mode=source_mode, **kwargs)


def get_gdp_unified(*, source_mode: str = "auto", **kwargs: Any):
    return get_macro_series_unified(MACRO_SERIES["gdp"], source_mode=source_mode, **kwargs)


def get_treasury_curve_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_rates_curve(source_mode=source_mode, **kwargs)


def get_sofr_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_macro_series("SOFR", source_mode=source_mode, **kwargs)


def get_effr_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_macro_series("EFFR", source_mode=source_mode, **kwargs)


def get_credit_spreads_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_macro_series("BAMLC0A0CM", source_mode=source_mode, **kwargs)


def _result_row(label: str, result: Any) -> dict[str, Any]:
    return {
        "label": label,
        "ok": result.ok,
        "provider": result.provider,
        "source": result.source,
        "freshness": result.freshness,
        "source_confidence": result.metadata.get("source_confidence", 0),
        "gaps": len(result.data_gaps),
        "route": result.metadata.get("route", {}).get("provider"),
        "proxy": result.is_proxy,
        "estimated": result.is_estimated,
    }


def build_macro_rates_dashboard_payload(*, source_mode: str = "auto") -> dict[str, Any]:
    results = {
        "cpi": get_cpi_unified(source_mode=source_mode),
        "pce": get_pce_unified(source_mode=source_mode),
        "unemployment": get_unemployment_unified(source_mode=source_mode),
        "gdp": get_gdp_unified(source_mode=source_mode),
        "treasury_curve": get_treasury_curve_unified(source_mode=source_mode),
        "sofr": get_sofr_unified(source_mode=source_mode),
        "effr": get_effr_unified(source_mode=source_mode),
        "credit_spreads": get_credit_spreads_unified(source_mode=source_mode),
    }
    rows = [_result_row(label, result) for label, result in results.items()]
    status_table = pd.DataFrame(rows) if pd is not None else rows
    return {
        "source_mode": source_mode,
        "results": results,
        "status_table": status_table,
        "data_gaps": [gap for result in results.values() for gap in result.data_gaps],
        "source_confidence": round(sum(result.metadata.get("source_confidence", 0) for result in results.values()) / max(1, len(results)), 1),
        "caveat": "Macro and rates data may be delayed, revised, or proxy-labeled depending on provider route.",
    }
