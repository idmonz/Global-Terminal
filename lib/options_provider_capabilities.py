from __future__ import annotations

from datetime import datetime, timezone
from importlib.util import find_spec
from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_options_provider_capability(provider: str = "manual", *, used_for_calculation: bool = False) -> dict[str, Any]:
    name = str(provider or "manual").lower()
    if name == "openbb":
        installed = find_spec("openbb") is not None
        return {
            "provider": "OpenBB optional capability snapshot",
            "capability": "option-chain discovery if separately installed/configured",
            "installed": installed,
            "key_required": "depends_on_provider",
            "last_checked": utc_timestamp(),
            "freshness": "not-used" if not used_for_calculation else "user-confirmed-required",
            "caveat": "OpenBB is optional and not a runtime dependency for Goal 12A calculations.",
            "used_for_calculation": used_for_calculation and installed,
            "notice": RESEARCH_ONLY_OPTIONS_NOTICE,
            "research_only": True,
        }
    if name in {"manual", "supplied", "user"}:
        return {
            "provider": "manual/supplied data",
            "capability": "local calculator inputs supplied by the user or fixture",
            "installed": True,
            "key_required": False,
            "last_checked": utc_timestamp(),
            "freshness": "supplied",
            "caveat": "No live option chain was fetched; calculation uses supplied fields only.",
            "used_for_calculation": bool(used_for_calculation),
            "notice": RESEARCH_ONLY_OPTIONS_NOTICE,
            "research_only": True,
        }
    return {
        "provider": provider,
        "capability": "unknown options provider capability",
        "installed": False,
        "key_required": "unknown",
        "last_checked": utc_timestamp(),
        "freshness": "unavailable",
        "caveat": "Provider is not configured; remain in calculator/manual mode.",
        "used_for_calculation": False,
        "notice": RESEARCH_ONLY_OPTIONS_NOTICE,
        "research_only": True,
    }


def build_options_source_snapshot(provider: str = "manual", *, used_for_calculation: bool = True, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    card = build_options_provider_capability(provider, used_for_calculation=used_for_calculation)
    return {"source": card["provider"], "freshness": card["freshness"], "confidence": "user-supplied" if provider in {"manual", "supplied", "user"} else "capability-only", "provider_card": card, "labels": [card["freshness"], "research-only"], **(extra or {})}


def inspect_options_provider_capabilities() -> dict[str, Any]:
    cards = [build_options_provider_capability("manual", used_for_calculation=True), build_options_provider_capability("openbb", used_for_calculation=False)]
    return {"ok": True, "cards": cards, "missing_option_chain_caveat": "If option-chain data is not supplied, the lab remains in calculator/manual mode.", "no_live_data_caveat": "Goal 12A does not fetch live option chains by default.", "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
