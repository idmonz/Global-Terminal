from __future__ import annotations

from typing import Any

from .api_contracts import to_json_safe


def _row_count(value: Any) -> int:
    safe = to_json_safe(value)
    if safe is None:
        return 0
    if isinstance(safe, list):
        return len(safe)
    if isinstance(safe, dict):
        for key in ["layers", "normalized_news", "events", "ledger", "rows", "data"]:
            item = safe.get(key)
            if isinstance(item, list):
                return len(item)
        return len(safe)
    return 1


def contract_summary_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return compact rows suitable for Streamlit dataframe rendering."""
    data = payload.get("data")
    unavailable = payload.get("unavailable") or []
    errors = payload.get("errors") or []
    source_status = payload.get("source_status") or []
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return [
        {"metric": "payload_type", "value": payload.get("payload_type"), "detail": "contract family"},
        {"metric": "contract_version", "value": payload.get("contract_version"), "detail": "stable envelope version"},
        {"metric": "data_rows", "value": _row_count(data), "detail": "top-level rows or records"},
        {"metric": "source_status_rows", "value": len(source_status), "detail": "provider/source status evidence"},
        {"metric": "unavailable_rows", "value": len(unavailable), "detail": "explicit gaps kept visible"},
        {"metric": "error_rows", "value": len(errors), "detail": "recoverable route/provider errors"},
        {"metric": "summary_status", "value": summary.get("status") or summary.get("ledger_status") or summary.get("selected_provider") or "", "detail": "payload summary signal"},
    ]


def contract_preview(payload: dict[str, Any], *, unavailable_limit: int = 5, caveat_limit: int = 5) -> dict[str, Any]:
    """Return a small JSON-safe preview without exposing bulky internal sections."""
    return {
        "contract_version": payload.get("contract_version"),
        "payload_type": payload.get("payload_type"),
        "generated_at": payload.get("generated_at"),
        "summary": to_json_safe(payload.get("summary") or {}),
        "unavailable_count": len(payload.get("unavailable") or []),
        "error_count": len(payload.get("errors") or []),
        "source_status_count": len(payload.get("source_status") or []),
        "unavailable_preview": to_json_safe((payload.get("unavailable") or [])[:unavailable_limit]),
        "caveats": [str(item) for item in (payload.get("caveats") or [])[:caveat_limit]],
    }


def contract_collection_rows(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for payload in payloads:
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        rows.append(
            {
                "payload_type": payload.get("payload_type"),
                "contract_version": payload.get("contract_version"),
                "data_rows": _row_count(payload.get("data")),
                "source_status_rows": len(payload.get("source_status") or []),
                "unavailable_rows": len(payload.get("unavailable") or []),
                "error_rows": len(payload.get("errors") or []),
                "status": summary.get("status") or summary.get("ledger_status") or summary.get("selected_provider") or "",
            }
        )
    return rows
