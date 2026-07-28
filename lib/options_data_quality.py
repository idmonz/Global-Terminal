from __future__ import annotations

from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE


def build_options_data_quality_status(input_payload: dict[str, Any] | None = None, *, option_chain_supplied: bool = False, stale: bool = False) -> dict[str, Any]:
    payload = input_payload or {}
    gaps = []
    for field in ["underlying_price", "strike", "time_to_expiry_years", "risk_free_rate", "volatility"]:
        if field not in payload or payload.get(field) is None:
            gaps.append(field)
    caveats = []
    if not option_chain_supplied:
        caveats.append("No option-chain table was supplied; calculator/manual mode is active.")
    if stale:
        caveats.append("Supplied option-chain timestamp is stale or unverified.")
    if gaps:
        caveats.append(f"Missing pricing inputs: {', '.join(gaps)}")
    return {"ok": not gaps, "manual_or_supplied_data_status": "supplied" if payload else "not_supplied", "missing_fields": gaps, "option_chain_supplied": option_chain_supplied, "stale_option_chain": stale, "caveats": caveats, "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
