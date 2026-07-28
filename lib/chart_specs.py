from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


CHART_SPEC_VERSION = "chart_spec.v1"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        number = float(value)
        if number != number or number in {float("inf"), float("-inf")}:
            return None
        return number
    except Exception:
        return None


def safe_text(value: Any, fallback: str = "") -> str:
    text = str(value if value is not None else fallback)
    return text if text else fallback


def record_series(
    rows: Iterable[dict[str, Any]],
    *,
    x_key: str,
    y_key: str,
    name: str,
    max_points: int = 80,
) -> dict[str, Any]:
    points = []
    for row in list(rows)[-max_points:]:
        y = safe_number(row.get(y_key))
        if y is None:
            continue
        points.append({"x": safe_text(row.get(x_key)), "y": y})
    return {"name": name, "points": points}


def build_chart_spec(
    *,
    chart_id: str,
    chart_type: str,
    title: str,
    series: list[dict[str, Any]],
    unit: str,
    provider: str,
    source_status: str,
    fetched_at: str | None,
    caveat: str,
    data_gap: str,
    x_axis: str = "time",
    y_axis: str = "value",
    dimensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "chart_spec_version": CHART_SPEC_VERSION,
        "chart_id": chart_id,
        "chart_type": chart_type,
        "title": title,
        "x_axis": x_axis,
        "y_axis": y_axis,
        "series": series,
        "unit": unit,
        "provider": provider,
        "source_status": source_status,
        "fetched_at": fetched_at,
        "freshness": source_status,
        "caveat": caveat,
        "data_gap": data_gap,
        "dimensions": dimensions or {},
        "not_financial_advice": True,
    }


def provider_status_row(
    *,
    provider: str,
    source: str,
    status: str,
    availability: str,
    row_count: int = 0,
    fetched_at: str | None = None,
    caveat: str = "",
    data_gap: str = "",
    recommended_action: str = "Inspect source status before using this panel.",
) -> dict[str, Any]:
    return {
        "provider": provider,
        "source": source,
        "status": status,
        "source_status": status,
        "freshness": status,
        "availability": availability,
        "row_count": row_count,
        "fetched_at": fetched_at,
        "cached": status == "cached",
        "estimated": status in {"fixture", "proxy/static", "inferred/proxy"},
        "paid_required": False,
        "caveat": caveat,
        "data_gap": data_gap,
        "recommended_action": recommended_action,
        "not_financial_advice": True,
    }
