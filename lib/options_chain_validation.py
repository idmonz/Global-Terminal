from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .options_chain_schema import REQUIRED_CANONICAL_COLUMNS


def _as_float(value: Any, field: str, errors: list[str], *, positive: bool = False, non_negative: bool = False, allow_none: bool = False) -> float | None:
    if value in (None, ""):
        if allow_none:
            return None
        errors.append(f"missing_{field}")
        return None
    try:
        out = float(value)
    except Exception:
        errors.append(f"invalid_numeric_{field}")
        return None
    if positive and out <= 0:
        errors.append(f"non_positive_{field}")
    if non_negative and out < 0:
        errors.append(f"negative_{field}")
    return out


def normalize_option_side(value: Any) -> str:
    text = str(value or "").strip().lower()
    aliases = {"c": "call", "call": "call", "calls": "call", "p": "put", "put": "put", "puts": "put"}
    if text not in aliases:
        raise ValueError("invalid_option_type")
    return aliases[text]


def parse_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except Exception:
        return str(value)


def validate_option_chain_row(row: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for field in REQUIRED_CANONICAL_COLUMNS:
        if field not in row or row.get(field) in (None, ""):
            if field == "source":
                continue
            errors.append(f"missing_{field}")
    option_type = ""
    try:
        option_type = normalize_option_side(row.get("option_type"))
    except ValueError as exc:
        errors.append(str(exc))
    strike = _as_float(row.get("strike"), "strike", errors, positive=True)
    bid = _as_float(row.get("bid"), "bid", errors, non_negative=True)
    ask = _as_float(row.get("ask"), "ask", errors, non_negative=True)
    underlying_price = _as_float(row.get("underlying_price"), "underlying_price", errors, positive=True)
    contract_multiplier = _as_float(row.get("contract_multiplier", 100.0), "contract_multiplier", errors, positive=True, allow_none=False)
    if bid is not None and ask is not None and bid > ask:
        errors.append("bid_greater_than_ask")
    for field in ["last", "mark", "mid", "volume", "open_interest", "implied_volatility", "delta", "gamma", "vega", "theta", "rho"]:
        if field in row and row.get(field) not in (None, ""):
            _as_float(row.get(field), field, errors, non_negative=field in {"last", "mark", "mid", "volume", "open_interest", "implied_volatility"})
    source = str(row.get("source") or "").strip() or "user_supplied_unknown_source"
    return {
        "ok": not errors,
        "errors": errors,
        "normalized": {
            **row,
            "option_type": option_type or str(row.get("option_type", "")),
            "strike": strike,
            "bid": bid,
            "ask": ask,
            "underlying_price": underlying_price,
            "contract_multiplier": contract_multiplier if contract_multiplier is not None else 100.0,
            "timestamp": parse_timestamp(row.get("timestamp")),
            "source": source,
        },
        "research_only": True,
    }


def validate_option_chain_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    caveated: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        validation = validate_option_chain_row({**row, "row_number": row.get("row_number", index)})
        if validation["ok"]:
            norm = validation["normalized"]
            flags: list[str] = []
            if norm.get("source") == "user_supplied_unknown_source":
                flags.append("missing_source_labeled")
            accepted.append({**norm, "quality_flags": flags, "row_number": row.get("row_number", index)})
            if flags:
                caveated.append({"row_number": row.get("row_number", index), "flags": flags})
        else:
            rejected.append({"row_number": row.get("row_number", index), "errors": validation["errors"], "row": row})
    return {"ok": len(rejected) == 0, "accepted_rows": accepted, "rejected_rows": rejected, "caveated_rows": caveated, "accepted_count": len(accepted), "rejected_count": len(rejected), "research_only": True}


def reject_or_caveat_invalid_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return validate_option_chain_rows(rows)
