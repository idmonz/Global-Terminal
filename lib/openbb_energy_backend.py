from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_router import request_energy_data


def get_petroleum_status_report_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_energy_data("energy.petroleum_status", source_mode=source_mode, **kwargs)


def get_short_term_energy_outlook_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_energy_data("energy.short_term_outlook", source_mode=source_mode, **kwargs)


def get_oil_inventory_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_energy_data("energy.inventory", source_mode=source_mode, **kwargs)


def get_oil_production_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_energy_data("energy.production", source_mode=source_mode, **kwargs)


def get_refinery_utilization_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_energy_data("energy.refinery", source_mode=source_mode, **kwargs)


def get_import_export_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_energy_data("energy.import_export", source_mode=source_mode, **kwargs)


def get_commodity_spot_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_energy_data("commodity.spot", source_mode=source_mode, **kwargs)


def _row(label: str, result: Any) -> dict[str, Any]:
    return {
        "dataset": label,
        "ok": result.ok,
        "provider": result.provider,
        "source": result.source,
        "freshness": result.freshness,
        "proxy": result.is_proxy,
        "estimated": result.is_estimated,
        "source_confidence": result.metadata.get("source_confidence", 0),
        "data_gaps": len(result.data_gaps),
    }


def build_energy_dashboard_payload(*, source_mode: str = "auto") -> dict[str, Any]:
    results = {
        "petroleum_status": get_petroleum_status_report_unified(source_mode=source_mode),
        "short_term_outlook": get_short_term_energy_outlook_unified(source_mode=source_mode),
        "inventory": get_oil_inventory_unified(source_mode=source_mode),
        "production": get_oil_production_unified(source_mode=source_mode),
        "refinery": get_refinery_utilization_unified(source_mode=source_mode),
        "import_export": get_import_export_unified(source_mode=source_mode),
        "commodity_spot": get_commodity_spot_unified(source_mode=source_mode),
    }
    rows = [_row(label, result) for label, result in results.items()]
    return {
        "source_mode": source_mode,
        "results": results,
        "status_table": pd.DataFrame(rows) if pd is not None else rows,
        "data_gaps": [gap for result in results.values() for gap in result.data_gaps],
        "source_confidence": round(sum(result.metadata.get("source_confidence", 0) for result in results.values()) / max(1, len(results)), 1),
        "caveat": "Energy datasets use native EIA when configured, optional OpenBB when available, and yfinance proxies only when labeled.",
    }
