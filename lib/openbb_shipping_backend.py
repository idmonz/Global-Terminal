from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_router import request_shipping_data


def get_port_info_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_shipping_data("shipping.port_info", source_mode=source_mode, **kwargs)


def get_port_volume_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_shipping_data("shipping.port_volume", source_mode=source_mode, **kwargs)


def get_chokepoint_info_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_shipping_data("shipping.chokepoint_info", source_mode=source_mode, **kwargs)


def get_chokepoint_volume_unified(*, source_mode: str = "auto", **kwargs: Any):
    return request_shipping_data("shipping.chokepoint_volume", source_mode=source_mode, **kwargs)


def build_shipping_chokepoint_payload(*, source_mode: str = "auto") -> dict[str, Any]:
    results = {
        "port_info": get_port_info_unified(source_mode=source_mode),
        "port_volume": get_port_volume_unified(source_mode=source_mode),
        "chokepoint_info": get_chokepoint_info_unified(source_mode=source_mode),
        "chokepoint_volume": get_chokepoint_volume_unified(source_mode=source_mode),
    }
    rows = []
    for label, result in results.items():
        rows.append(
            {
                "dataset": label,
                "ok": result.ok,
                "provider": result.provider,
                "source": result.source,
                "freshness": result.freshness,
                "proxy": True,
                "source_confidence": result.metadata.get("source_confidence", 0),
                "data_gaps": len(result.data_gaps),
                "caveat": "Static metadata / proxy. No live AIS is claimed.",
            }
        )
    return {
        "source_mode": source_mode,
        "results": results,
        "status_table": pd.DataFrame(rows) if pd is not None else rows,
        "data_gaps": [gap for result in results.values() for gap in result.data_gaps],
        "caveat": "Port/chokepoint volume data is provider-dependent. Static registry fallback is labeled proxy.",
    }
