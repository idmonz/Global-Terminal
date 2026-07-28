from __future__ import annotations

from typing import Any

from .options_chain_schema import COLUMN_ALIASES
from .options_chain_validation import validate_option_chain_rows


def _clean_header(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def infer_option_chain_columns(headers: list[str]) -> dict[str, str]:
    normalized_headers = {_clean_header(h): h for h in headers}
    mapping: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _clean_header(alias)
            if key in normalized_headers:
                mapping[canonical] = normalized_headers[key]
                break
    return mapping


def normalize_option_chain_rows(raw_rows: list[dict[str, Any]], column_map: dict[str, str] | None = None) -> list[dict[str, Any]]:
    if not raw_rows:
        return []
    headers = list(raw_rows[0].keys())
    mapping = column_map or infer_option_chain_columns(headers)
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows, start=1):
        row: dict[str, Any] = {"row_number": index}
        for canonical, source_col in mapping.items():
            row[canonical] = raw.get(source_col)
        # Preserve unknown source as an explicit label.
        if not row.get("underlying"):
            row["underlying"] = row.get("symbol") or row.get("root") or row.get("ticker") or row.get("asset")
        if not row.get("root"):
            row["root"] = row.get("underlying")
        if not row.get("source"):
            row["source"] = "user_supplied_unknown_source"
        if not row.get("provider") and row.get("source"):
            row["provider"] = row.get("source")
        out.append(row)
    return out


def normalize_and_validate_option_chain(raw_rows: list[dict[str, Any]], column_map: dict[str, str] | None = None) -> dict[str, Any]:
    rows = normalize_option_chain_rows(raw_rows, column_map=column_map)
    return validate_option_chain_rows(rows)
