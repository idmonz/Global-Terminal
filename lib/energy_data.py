from __future__ import annotations

from typing import Any

import pandas as pd
import requests

from .config import get_settings
from .data_status import error_result, ok_result
from .market_data import fetch_many_price_histories


EIA_SERIES = {
    "wti_spot": {"route": "petroleum/pri/spt/data", "series": "RWTC", "label": "WTI spot"},
    "brent_spot": {"route": "petroleum/pri/spt/data", "series": "RBRTE", "label": "Brent spot"},
    "crude_inventories": {"route": "petroleum/stoc/wstk/data", "series": "WCESTUS1", "label": "US crude inventories"},
    "cushing_inventories": {"route": "petroleum/stoc/wstk/data", "series": "W_EPC0_SAX_YCUOK_MBBL", "label": "Cushing inventories"},
    "us_crude_production": {"route": "petroleum/sum/sndw/data", "series": "WCRFPUS2", "label": "US crude production"},
    "us_crude_imports": {"route": "petroleum/move/wkly/data", "series": "WCRIMUS2", "label": "US crude imports"},
    "us_crude_exports": {"route": "petroleum/move/wkly/data", "series": "WCREXUS2", "label": "US crude exports"},
    "refinery_utilization": {"route": "petroleum/pnp/wiup/data", "series": "WPULEUS3", "label": "Refinery utilization"},
    "gasoline_stocks": {"route": "petroleum/stoc/wstk/data", "series": "WGTSTUS1", "label": "Gasoline stocks"},
    "distillate_stocks": {"route": "petroleum/stoc/wstk/data", "series": "WDISTUS1", "label": "Distillate stocks"},
    "product_supplied": {"route": "petroleum/cons/wpsup/data", "series": "WTTUPUS2", "label": "Product supplied"},
    "spr_stocks": {"route": "petroleum/stoc/wstk/data", "series": "WCSSTUS1", "label": "SPR stocks"},
}

ENERGY_FALLBACK_TICKERS = ["CL=F", "BZ=F", "RB=F", "HO=F", "NG=F", "XLE", "DX-Y.NYB", "^TNX"]


def _numeric_series(values) -> pd.Series:
    if hasattr(values, "columns"):
        values = values.bfill(axis=1).iloc[:, 0]
    return pd.to_numeric(values, errors="coerce")


def get_eia_api_key_status() -> object:
    if get_settings().eia_api_key:
        return ok_result({"configured": True}, source="EIA_API_KEY", provider="eia", coverage="key configured")
    return error_result(source="EIA_API_KEY", provider="eia", error="EIA_API_KEY is not configured. EIA fundamentals are unavailable in free mode.")


def get_eia_series(series_id_or_route: str, params: dict | None = None) -> tuple[pd.DataFrame, object]:
    settings = get_settings()
    if not settings.eia_api_key:
        return pd.DataFrame(), error_result(source="EIA v2", provider="eia", error="EIA_API_KEY is not configured.")
    params = dict(params or {})
    route = params.pop("route", None)
    series_id = series_id_or_route
    if series_id_or_route in EIA_SERIES:
        spec = EIA_SERIES[series_id_or_route]
        route = route or spec["route"]
        series_id = spec["series"]
    route = route or series_id_or_route
    url = f"https://api.eia.gov/v2/{route.lstrip('/')}/"
    request_params = {"api_key": settings.eia_api_key, "frequency": params.pop("frequency", "weekly"), "data[0]": "value", "facets[series][]": series_id}
    request_params.update(params)
    try:
        response = requests.get(url, params=request_params, timeout=20)
        if response.status_code in {401, 403}:
            return pd.DataFrame(), error_result(source=url, provider="eia", error="EIA API rejected the request; check key and endpoint access.", is_paid_required=False)
        response.raise_for_status()
        payload = response.json()
        data = _parse_eia_payload(payload)
        if data.empty:
            return data, error_result(source=url, provider="eia", error="EIA response did not include usable rows.", warning="Endpoint shape may differ.")
        return data, ok_result(data, source=url, provider="eia", coverage=f"{len(data)} rows")
    except ValueError as exc:
        return pd.DataFrame(), error_result(source=url, provider="eia", error=f"Invalid JSON from EIA: {exc}")
    except Exception as exc:
        return pd.DataFrame(), error_result(source=url, provider="eia", error=str(exc))


def _parse_eia_payload(payload: Any) -> pd.DataFrame:
    if not isinstance(payload, dict):
        return pd.DataFrame()
    response = payload.get("response", {})
    rows = response.get("data", []) if isinstance(response, dict) else []
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    value_col = "value" if "value" in frame.columns else frame.columns[-1]
    period_col = "period" if "period" in frame.columns else "date" if "date" in frame.columns else frame.columns[0]
    frame = frame.rename(columns={period_col: "date", value_col: "value"})
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return frame.dropna(subset=["value"], how="all")


def get_yfinance_energy_fallback(period: str = "6mo") -> tuple[pd.DataFrame, object]:
    histories, status = fetch_many_price_histories(ENERGY_FALLBACK_TICKERS, period=period)
    rows = []
    for ticker, frame in histories.items():
        if "close" not in frame.columns:
            continue
        close = _numeric_series(frame["close"]).dropna()
        if close.empty:
            continue
        clean = frame.loc[close.index]
        if clean.empty:
            continue
        rows.append(
            {
                "ticker": ticker,
                "latest_price": float(close.iloc[-1]),
                "daily_return": float(close.pct_change().iloc[-1]) if len(close) > 1 else 0.0,
                "rows": len(clean),
                "source_status": "real/delayed yfinance",
            }
        )
    data = pd.DataFrame(rows)
    if data.empty:
        return data, error_result(source="yfinance energy fallback", provider="yfinance", error=status.error or "No energy fallback tickers returned usable data.")
    return data, ok_result(data, source="yfinance energy fallback", provider="yfinance", warning=status.warning, coverage=f"{len(data)}/{len(ENERGY_FALLBACK_TICKERS)} tickers")


def get_wti_brent_prices() -> tuple[pd.DataFrame, object]:
    return get_yfinance_energy_fallback(period="1y")


def _eia_named_series(name: str) -> tuple[pd.DataFrame, object]:
    if name not in EIA_SERIES:
        return pd.DataFrame(), error_result(source="EIA metadata", provider="eia", error=f"Unknown EIA series: {name}")
    return get_eia_series(name)


def get_crude_inventories() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("crude_inventories")


def get_cushing_inventories() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("cushing_inventories")


def get_us_crude_production() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("us_crude_production")


def get_us_crude_imports() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("us_crude_imports")


def get_us_crude_exports() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("us_crude_exports")


def get_refinery_utilization() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("refinery_utilization")


def get_gasoline_stocks() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("gasoline_stocks")


def get_distillate_stocks() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("distillate_stocks")


def get_product_supplied() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("product_supplied")


def get_spr_stocks_if_available() -> tuple[pd.DataFrame, object]:
    return _eia_named_series("spr_stocks")


def build_energy_fundamentals_dashboard(enable_eia: bool = True) -> tuple[dict[str, pd.DataFrame], object]:
    datasets: dict[str, pd.DataFrame] = {}
    statuses = []
    if enable_eia:
        for name, getter in [
            ("crude_inventories", get_crude_inventories),
            ("cushing_inventories", get_cushing_inventories),
            ("production", get_us_crude_production),
            ("imports", get_us_crude_imports),
            ("exports", get_us_crude_exports),
            ("refinery_utilization", get_refinery_utilization),
            ("gasoline_stocks", get_gasoline_stocks),
            ("distillate_stocks", get_distillate_stocks),
            ("product_supplied", get_product_supplied),
            ("spr_stocks", get_spr_stocks_if_available),
        ]:
            data, status = getter()
            datasets[name] = data
            statuses.append(status)
    fallback, fallback_status = get_yfinance_energy_fallback()
    datasets["yfinance_fallback"] = fallback
    statuses.append(fallback_status)
    ok_count = sum(status.ok for status in statuses)
    warning = "; ".join((status.error or status.warning or "") for status in statuses if not status.ok or status.warning)[:500] or None
    if ok_count == 0:
        return datasets, error_result(source="EIA + yfinance", provider="energy_data", error=warning or "No energy feeds available.")
    return datasets, ok_result(datasets, source="EIA + yfinance", provider="energy_data", warning=warning, coverage=f"{ok_count}/{len(statuses)} feeds")


def build_unified_energy_dashboard(source_mode: str = "auto") -> dict[str, Any]:
    from .energy_market_impact import build_energy_market_impact_cards
    from .openbb_energy_backend import build_energy_dashboard_payload

    payload = build_energy_dashboard_payload(source_mode=source_mode)
    payload["market_impact_cards"] = build_energy_market_impact_cards(payload)
    return payload
