from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

WATCHLIST_ITEM_TYPES = {
    "asset", "crypto", "commodity", "equity", "etf", "index", "fx", "rate",
    "region", "country", "chokepoint", "port", "provider", "strategy",
    "event_theme", "portfolio", "report_topic",
}

@dataclass(frozen=True)
class WatchlistItem:
    item_id: str
    item_type: str
    display_name: str
    symbol: str = ""
    asset_class: str = ""
    exchange: str = ""
    region: str = ""
    country: str = ""
    tags: list[str] = field(default_factory=list)
    watch_reason: str = ""
    default_command: str = ""
    default_page: str = "pages/20_Watchlist_Alerts.py"
    source: str = "manual"
    active: bool = True
    created_at: str = ""
    updated_at: str = ""
    metadata_json: dict[str, Any] = field(default_factory=dict)


def validate_watchlist_item_type(item_type: str) -> str:
    normalized = str(item_type or "asset").lower().strip()
    if normalized not in WATCHLIST_ITEM_TYPES:
        raise ValueError(f"Unsupported watchlist item_type: {item_type}")
    return normalized


def infer_item_type(value: str) -> str:
    text = str(value or "").strip()
    upper = text.upper()
    if upper.startswith("PROVIDER:"):
        return "provider"
    if upper in {"RED SEA", "STRAIT OF HORMUZ", "SUEZ CANAL", "PANAMA CANAL"}:
        return "chokepoint"
    if upper.endswith("USDT") or upper in {"BTC", "ETH"}:
        return "crypto"
    if upper in {"CL1!", "GC1!", "HG1!", "NG1!"}:
        return "commodity"
    return "asset"


def item_to_dict(item: WatchlistItem) -> dict[str, Any]:
    return asdict(item)

