from __future__ import annotations

from typing import Any

from .mcp_context_router import (
    build_financial_context_packet,
    build_macro_energy_context_packet,
    build_mcp_ready_endpoint_manifest,
    build_portfolio_context_packet,
    build_screener_context_packet,
    build_war_room_context_packet,
    compress_context_for_llm,
)
from .openbb_bridge import OPENBB_CAVEAT, is_openbb_installed


def build_openbb_financial_context_packet(financial_payload: dict[str, Any]) -> dict[str, Any]:
    packet = build_financial_context_packet(financial_payload)
    packet.update({"openbb_installed": is_openbb_installed(), "openbb_caveat": OPENBB_CAVEAT})
    return packet


def build_openbb_portfolio_context_packet(portfolio_payload: dict[str, Any]) -> dict[str, Any]:
    packet = build_portfolio_context_packet(portfolio_payload)
    packet.update({"openbb_installed": is_openbb_installed(), "openbb_caveat": OPENBB_CAVEAT})
    return packet


def build_openbb_screener_context_packet(screener_payload: dict[str, Any]) -> dict[str, Any]:
    packet = build_screener_context_packet(screener_payload)
    packet.update({"openbb_installed": is_openbb_installed(), "openbb_caveat": OPENBB_CAVEAT})
    return packet


def build_openbb_macro_energy_context_packet(macro_energy_payload: dict[str, Any]) -> dict[str, Any]:
    packet = build_macro_energy_context_packet(macro_energy_payload)
    packet.update({"openbb_installed": is_openbb_installed(), "openbb_caveat": OPENBB_CAVEAT})
    return packet


def build_openbb_war_room_context_packet(war_room_payload: dict[str, Any]) -> dict[str, Any]:
    packet = build_war_room_context_packet(war_room_payload)
    packet.update({"openbb_installed": is_openbb_installed(), "openbb_caveat": OPENBB_CAVEAT})
    return packet


def build_openbb_ai_context_bundle(
    *,
    financial: dict[str, Any] | None = None,
    portfolio: dict[str, Any] | None = None,
    screener: dict[str, Any] | None = None,
    macro_energy: dict[str, Any] | None = None,
    war_room: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packets = {}
    if financial is not None:
        packets["financial"] = build_openbb_financial_context_packet(financial)
    if portfolio is not None:
        packets["portfolio"] = build_openbb_portfolio_context_packet(portfolio)
    if screener is not None:
        packets["screener"] = build_openbb_screener_context_packet(screener)
    if macro_energy is not None:
        packets["macro_energy"] = build_openbb_macro_energy_context_packet(macro_energy)
    if war_room is not None:
        packets["war_room"] = build_openbb_war_room_context_packet(war_room)
    return {
        "packets": packets,
        "compressed": compress_context_for_llm(packets),
        "mcp_manifest": build_mcp_ready_endpoint_manifest(),
        "caveat": "OpenBB AI context is compact, source-labeled, and not sent to an LLM unless a page button triggers analysis.",
    }


def build_mcp_ready_openbb_endpoint_manifest() -> list[dict[str, Any]]:
    return build_mcp_ready_endpoint_manifest()
