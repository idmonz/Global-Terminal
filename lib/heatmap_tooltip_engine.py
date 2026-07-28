from __future__ import annotations

from typing import Any


def _line(label: str, value: Any) -> str:
    return f"{label}: {'N/A' if value is None else value}"


def build_heatmap_tooltip(tile: dict[str, Any]) -> str:
    metadata = tile.get("metadata", {})
    raw = tile.get("raw", {})
    lines = [
        _line("Item", tile.get("label")),
        _line("Group", tile.get("group")),
        _line("Current value", raw.get("price") or raw.get("value")),
        _line("Change/score", tile.get("color_value")),
        _line("Source", metadata.get("source")),
        _line("Freshness", metadata.get("freshness")),
        _line("Status", metadata.get("truth_label")),
        _line("Confidence", metadata.get("confidence")),
        _line("Data gaps", ", ".join(metadata.get("data_gaps") or []) or "none reported"),
    ]
    suggestion = raw.get("command") or raw.get("next_command")
    if suggestion:
        lines.append(_line("Next drilldown", suggestion))
    return "\n".join(lines)


def build_equity_tile_tooltip(tile: dict[str, Any]) -> str:
    raw = tile.get("raw", {})
    return build_heatmap_tooltip({**tile, "raw": {**raw, "next_command": raw.get("next_command") or f"{raw.get('ticker', tile.get('label'))} FA"}})


def build_crypto_tile_tooltip(tile: dict[str, Any]) -> str:
    raw = tile.get("raw", {})
    extra = [
        _line("Funding", raw.get("funding_rate")),
        _line("Open interest", raw.get("open_interest")),
        _line("OI change", raw.get("open_interest_change")),
        _line("Long/short", raw.get("long_short_ratio") or raw.get("global_long_short_ratio")),
        _line("Liquidation pressure", raw.get("liquidation_pressure")),
        _line("TVL", raw.get("tvl")),
    ]
    return build_heatmap_tooltip(tile) + "\n" + "\n".join(extra)


def build_portfolio_tile_tooltip(tile: dict[str, Any]) -> str:
    raw = tile.get("raw", {})
    return build_heatmap_tooltip(tile) + "\n" + "\n".join([_line("Weight", raw.get("weight")), _line("Risk contribution", raw.get("risk_contribution"))])


def build_provider_tile_tooltip(tile: dict[str, Any]) -> str:
    raw = tile.get("raw", {})
    return build_heatmap_tooltip(tile) + "\n" + "\n".join([_line("Configured", raw.get("configured")), _line("Key status", raw.get("key_status") or raw.get("status")), _line("Last probe", raw.get("checked_at")), _line("Latency", raw.get("latency_ms"))])


def build_war_room_tile_tooltip(tile: dict[str, Any]) -> str:
    raw = tile.get("raw", {})
    return build_heatmap_tooltip(tile) + "\n" + "\n".join([_line("Event type", raw.get("event_type")), _line("Location", raw.get("location")), _line("Linked assets", raw.get("linked_assets") or raw.get("asset_tags")), _line("Map layer", raw.get("layer"))])


def build_energy_tile_tooltip(tile: dict[str, Any]) -> str:
    raw = tile.get("raw", {})
    return build_heatmap_tooltip(tile) + "\n" + "\n".join([_line("Chokepoint", raw.get("chokepoint") or raw.get("name")), _line("Energy assets", raw.get("energy_assets") or raw.get("assets")), _line("Shipping/port status", raw.get("shipping_status")), _line("Weather risk", raw.get("weather_risk")), _line("Proxy caveat", raw.get("caveat") or "Proxy-labeled when live feeds are unavailable")])
