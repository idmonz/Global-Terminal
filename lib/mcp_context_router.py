from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .endpoint_catalog import build_internal_endpoint_catalog


NO_ADVICE_DISCLOSURE = "Backtests and model-estimated forward distributions are for research only. They are not financial advice, not predictions, and not recommendations. Past performance does not guarantee future results."


def _compact(value: Any, *, max_rows: int = 8, max_chars: int = 900) -> Any:
    if pd is not None and isinstance(value, pd.DataFrame):
        return {"columns": list(value.columns), "row_count": int(len(value)), "sample_rows": value.head(max_rows).to_dict(orient="records")}
    if hasattr(value, "to_dict") and hasattr(value, "head"):
        try:
            return {"columns": list(value.columns), "row_count": int(len(value)), "sample_rows": value.head(max_rows).to_dict(orient="records")}
        except Exception:
            pass
    if isinstance(value, dict):
        return {key: _compact(val, max_rows=max_rows, max_chars=max_chars) for key, val in value.items()}
    if isinstance(value, list):
        return [_compact(item, max_rows=max_rows, max_chars=max_chars) for item in value[:max_rows]]
    text = str(value)
    return text[:max_chars]


def build_financial_context_packet(financial_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_type": "financial",
        "payload": _compact(financial_payload),
        "data_gaps": _compact(financial_payload.get("data_gaps", [])),
        "source_confidence": financial_payload.get("source_confidence"),
        "disclosure": "No financial advice. Estimates/segments/geography are included only when provider-supplied.",
    }


def build_portfolio_context_packet(portfolio_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_type": "portfolio",
        "payload": _compact(portfolio_payload),
        "data_gaps": _compact(portfolio_payload.get("data_gaps", [])),
        "source_confidence": portfolio_payload.get("source_confidence"),
        "disclosure": NO_ADVICE_DISCLOSURE,
    }


def build_screener_context_packet(screener_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_type": "screener",
        "payload": _compact(screener_payload),
        "data_gaps": _compact(screener_payload.get("data_gaps", [])),
        "source_confidence": screener_payload.get("source_confidence"),
        "disclosure": "Screener rows are research candidates or watchlist context only.",
    }


def build_macro_energy_context_packet(macro_energy_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_type": "macro_energy",
        "payload": _compact(macro_energy_payload),
        "data_gaps": _compact(macro_energy_payload.get("data_gaps", [])),
        "source_confidence": macro_energy_payload.get("source_confidence"),
        "disclosure": "Macro/energy/chokepoint context is informational and may include proxy-labeled evidence.",
    }


def build_war_room_context_packet(war_room_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_type": "war_room",
        "payload": _compact(war_room_payload),
        "data_gaps": _compact(war_room_payload.get("data_gaps", [])),
        "source_confidence": war_room_payload.get("source_confidence"),
        "disclosure": "War Room OSINT context requires source verification and may include heuristic/proxy layers.",
    }


def compress_context_for_llm(packet: dict[str, Any], *, max_chars: int = 6000) -> dict[str, Any]:
    compacted = _compact(packet, max_chars=max_chars)
    text = str(compacted)
    return {"packet": compacted, "text": text[:max_chars], "truncated": len(text) > max_chars}


def route_context_to_ai_provider(packet: dict[str, Any], *, provider: str = "auto", execute: bool = False):
    prepared = compress_context_for_llm(packet)
    prepared["provider"] = provider
    prepared["execute"] = execute
    prepared["policy"] = "No automatic LLM call; execute must be explicitly true."
    if not execute:
        return prepared
    from .ai_analysis import analyze_overview_neutral

    return analyze_overview_neutral(prepared, preferred=provider)


def build_mcp_ready_endpoint_manifest() -> list[dict[str, Any]]:
    manifest = []
    for endpoint, definition in build_internal_endpoint_catalog().items():
        manifest.append(
            {
                "endpoint_id": endpoint,
                "input_schema": {
                    "symbol": "optional string",
                    "symbols": "optional list[string]",
                    "start_date": "optional date",
                    "end_date": "optional date",
                    "source_mode": "auto|native_only|openbb_preferred|openbb_only|provider_specific",
                },
                "output_schema": {
                    "ok": "bool",
                    "data": "tabular or structured payload",
                    "provider": "string",
                    "freshness": "fresh|stale|missing|estimated|error",
                    "data_gaps": "list",
                    "metadata": "dict",
                },
                "source_fallback": {
                    "native": definition.native_providers,
                    "openbb_candidates": definition.openbb_candidate_paths,
                },
                "caveat": definition.caveat,
            }
        )
    return manifest
