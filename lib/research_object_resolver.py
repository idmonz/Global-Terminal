from __future__ import annotations

import re
from typing import Any

_ASSET_RE = re.compile(r"^[A-Z]{1,6}([./-][A-Z0-9]{1,6})?$")
_CRYPTO_RE = re.compile(r"^(BTC|ETH|SOL|BNB|XRP|ADA|DOGE|AVAX|LINK)[A-Z0-9._-]{0,12}$")
_PROVIDER_WORDS = {"FRED", "EIA", "OPENBB", "YFINANCE", "BINANCE", "COINGECKO", "GDELT", "USGS", "NOAA"}
_REGION_WORDS = {"RED SEA", "SUEZ", "HORMUZ", "KOREA", "MENA", "EUROPE", "EAST ASIA", "UKRAINE", "BLACK SEA"}


def resolve_research_object(query: str) -> dict[str, Any]:
    raw = str(query or "").strip()
    normalized = " ".join(raw.upper().split())
    if not normalized:
        return {"query": raw, "object_type": "empty", "normalized": "", "confidence": "low", "research_only": True}
    if normalized.startswith("STRATEGY") or "ENSEMBLE" in normalized:
        return {"query": raw, "object_type": "strategy", "normalized": normalized, "display_name": raw, "confidence": "medium", "research_only": True}
    if normalized in _PROVIDER_WORDS or normalized.endswith(" PROVIDER"):
        return {"query": raw, "object_type": "provider", "normalized": normalized, "display_name": raw, "confidence": "high", "research_only": True}
    if normalized in _REGION_WORDS or any(token in normalized for token in ["SEA", "SUEZ", "HORMUZ", "KOREA", "UKRAINE"]):
        return {"query": raw, "object_type": "region", "normalized": normalized, "display_name": raw, "confidence": "medium", "research_only": True}
    if _CRYPTO_RE.match(normalized) or normalized.endswith("USDT") or normalized.endswith("USDTPERP"):
        return {"query": raw, "object_type": "crypto", "normalized": normalized, "display_name": raw, "confidence": "high", "research_only": True}
    if _ASSET_RE.match(normalized.replace(":", "")):
        return {"query": raw, "object_type": "asset", "normalized": normalized, "display_name": raw, "confidence": "medium", "research_only": True}
    return {"query": raw, "object_type": "topic", "normalized": normalized, "display_name": raw, "confidence": "low", "research_only": True}
