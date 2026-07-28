from __future__ import annotations
from typing import Any

ALIASES: dict[str, set[str]] = {
    "red sea": {"red sea", "bab el-mandeb", "bab el mandeb", "suez", "shipping lane", "shipping", "houthi"},
    "strait of hormuz": {"hormuz", "strait of hormuz", "persian gulf", "iran", "tanker", "oil chokepoint"},
    "suez": {"suez", "suez canal", "egypt", "red sea"},
    "panama canal": {"panama canal", "panama", "canal drought", "shipping"},
    "taiwan strait": {"taiwan strait", "taiwan", "tsmc", "semiconductor", "china"},
    "black sea": {"black sea", "ukraine", "russia", "grain", "wheat", "crimea"},
    "middle east": {"middle east", "mena", "gaza", "israel", "iran", "iraq", "saudi", "red sea", "hormuz"},
    "korea": {"korea", "south korea", "kospi", "krw", "seoul"},
    "china": {"china", "cn", "cny", "shanghai", "hang seng", "taiwan strait"},
    "oil": {"oil", "crude", "brent", "wti", "cl1", "cl1!", "bz", "xle", "energy", "opec"},
    "crypto": {"crypto", "btc", "btcusdt", "bitcoin", "eth", "ethereum", "funding", "open interest", "liquidation"},
    "fred": {"fred", "federal reserve economic data", "st louis fed"},
    "eia": {"eia", "energy information administration", "crude inventory", "weekly petroleum"},
    "binance": {"binance", "btcusdt", "funding", "oi", "open interest"},
    "coingecko": {"coingecko", "crypto price", "token"},
    "defillama": {"defillama", "tvl", "defi"},
}


def normalize_token(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ").split())


def aliases_for(value: Any) -> set[str]:
    key = normalize_token(value)
    out = {key} if key else set()
    for canonical, aliases in ALIASES.items():
        if key == canonical or key in aliases or canonical in key:
            out.update(aliases)
            out.add(canonical)
        elif key and any(a in key or key in a for a in aliases):
            out.update(aliases)
            out.add(canonical)
    return {normalize_token(x) for x in out if normalize_token(x)}


def build_watchlist_alias_terms(item: dict[str, Any]) -> set[str]:
    fields = [item.get("symbol"), item.get("display_name"), item.get("asset_class"), item.get("region"), item.get("country"), item.get("item_type"), item.get("source")]
    for tag in item.get("tags") or []:
        fields.append(tag)
    terms: set[str] = set()
    for value in fields:
        terms.update(aliases_for(value))
    return {term for term in terms if term}
