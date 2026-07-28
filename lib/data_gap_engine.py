from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_contracts import DataGap


def _frame(data: Any):
    if pd is None:
        return None
    if data is None:
        return pd.DataFrame()
    if isinstance(data, pd.DataFrame):
        return data
    try:
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def detect_data_gaps(data: Any, required_fields: list[str] | None = None, *, endpoint: str = "", provider: str | None = None) -> list[DataGap]:
    frame = _frame(data)
    gaps: list[DataGap] = []
    if pd is None:
        return [DataGap(field="pandas", reason="pandas is not installed.", severity="high", provider=provider, endpoint=endpoint, is_blocking=True)]
    if frame is None or frame.empty:
        gaps.append(DataGap(field=endpoint or "dataset", reason="No usable rows returned.", severity="high", provider=provider, endpoint=endpoint, is_blocking=True))
    fields = [str(field).strip().lower().replace(" ", "_") for field in required_fields or []]
    columns = {str(col).strip().lower().replace(" ", "_") for col in getattr(frame, "columns", [])}
    for field in fields:
        if field not in columns:
            gaps.append(DataGap(field=field, reason="Required field is missing.", severity="high", provider=provider, endpoint=endpoint, is_blocking=True))
        elif frame[field].dropna().empty if field in frame.columns else False:
            gaps.append(DataGap(field=field, reason="Required field is empty.", severity="medium", provider=provider, endpoint=endpoint, is_blocking=False))
    return gaps


def classify_data_gap_severity(gap: DataGap | dict[str, Any] | str) -> str:
    if isinstance(gap, DataGap):
        return gap.severity
    if isinstance(gap, dict):
        return str(gap.get("severity") or ("high" if gap.get("is_blocking") else "medium"))
    text = str(gap).lower()
    if "missing key" in text or "required" in text:
        return "high"
    if "optional" in text or "proxy" in text:
        return "low"
    return "medium"


def build_data_gap_cards(gaps: list[DataGap | dict[str, Any] | str] | None = None) -> list[dict[str, Any]]:
    cards = []
    for gap in gaps or []:
        if isinstance(gap, DataGap):
            payload = gap.to_dict()
        elif isinstance(gap, dict):
            payload = dict(gap)
        else:
            payload = {"field": "data", "reason": str(gap), "severity": classify_data_gap_severity(gap)}
        payload.setdefault("severity", classify_data_gap_severity(payload))
        payload.setdefault("is_blocking", payload["severity"] == "high")
        payload["label"] = str(payload.get("field") or "data").replace("_", " ").title()
        cards.append(payload)
    return cards


def build_missing_provider_key_cards(keys: list[str] | None = None, *, provider: str = "provider") -> list[dict[str, Any]]:
    return [
        {
            "field": key,
            "provider": provider,
            "severity": "medium",
            "reason": "Optional provider key is not configured. Secret values are never displayed.",
            "is_blocking": False,
            "label": "Optional Provider Key",
        }
        for key in keys or []
    ]


def build_proxy_data_warning(label: str = "dataset") -> dict[str, Any]:
    return {
        "field": label,
        "severity": "low",
        "reason": "This output is proxy-labeled and should not be treated as an official source field.",
        "is_proxy": True,
        "is_blocking": False,
    }


def build_unavailable_endpoint_warning(endpoint: str, *, provider: str | None = None, reason: str | None = None) -> dict[str, Any]:
    return {
        "field": endpoint,
        "provider": provider,
        "severity": "high",
        "reason": reason or "Endpoint is unavailable from the configured route.",
        "is_blocking": True,
    }
