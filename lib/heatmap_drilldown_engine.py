from __future__ import annotations

from typing import Any


def heatmap_symbol_to_page_route(symbol: str) -> dict[str, str]:
    return {"page": "pages/15_Financial_Terminal.py", "command": f"{str(symbol).upper()} FA"}


def heatmap_group_to_screener_filter(group: str) -> dict[str, str]:
    return {"page": "pages/13_Screener.py", "command": f"SCREEN {group}"}


def heatmap_provider_to_provider_center_route(provider: str) -> dict[str, str]:
    return {"page": "pages/17_Data_Provider_Center.py", "command": f"DATA PROBE {provider}"}


def heatmap_asset_to_financial_terminal_route(asset: str) -> dict[str, str]:
    return heatmap_symbol_to_page_route(asset)


def heatmap_crypto_to_crypto_intelligence_route(symbol: str) -> dict[str, str]:
    return {"page": "pages/8_Crypto_Intelligence.py", "command": f"{str(symbol).upper()} CRYPTO"}


def heatmap_portfolio_to_portfolio_lab_route(symbol: str) -> dict[str, str]:
    return {"page": "pages/16_Portfolio_Quant_Lab.py", "command": f"{str(symbol).upper()} PORT"}


def heatmap_region_to_war_room_route(region: str) -> dict[str, str]:
    return {"page": "pages/14_War_Room.py", "command": f"WAR ROOM {region}"}


def heatmap_energy_to_energy_page_route(item: str) -> dict[str, str]:
    return {"page": "pages/9_Energy_Geopolitics.py", "command": f"{item} ENERGY"}


def build_heatmap_drilldown_target(tile: dict[str, Any]) -> dict[str, Any]:
    raw = tile.get("raw", {})
    group = str(tile.get("group") or raw.get("group") or "")
    symbol = str(raw.get("symbol") or raw.get("ticker") or tile.get("label") or "")
    tile_type = str(raw.get("tile_type") or raw.get("asset_class") or raw.get("domain") or "").lower()
    if "provider" in tile_type or raw.get("provider_id"):
        target = heatmap_provider_to_provider_center_route(str(raw.get("provider_id") or tile.get("label")))
    elif "crypto" in tile_type or symbol.endswith("-USD") or symbol in {"BTC", "ETH", "SOL"}:
        target = heatmap_crypto_to_crypto_intelligence_route(symbol)
    elif "portfolio" in tile_type or raw.get("weight") is not None:
        target = heatmap_portfolio_to_portfolio_lab_route(symbol)
    elif "energy" in tile_type or raw.get("chokepoint"):
        target = heatmap_energy_to_energy_page_route(str(raw.get("chokepoint") or symbol or group))
    elif "region" in tile_type or raw.get("region"):
        target = heatmap_region_to_war_room_route(str(raw.get("region") or group))
    elif symbol:
        target = heatmap_symbol_to_page_route(symbol)
    else:
        target = heatmap_group_to_screener_filter(group or "market")
    return {"label": tile.get("label"), **target}


def build_heatmap_command_suggestion(tile: dict[str, Any]) -> str:
    return build_heatmap_drilldown_target(tile)["command"]
