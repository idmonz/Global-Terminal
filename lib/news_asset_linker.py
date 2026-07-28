from __future__ import annotations

import re
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


DOMAIN_KEYWORDS = {
    "macro": ["gdp", "growth", "jobs", "inflation", "recession", "tariff", "trade"],
    "rates": ["fed", "rate", "treasury", "yield", "central bank", "bond"],
    "FX": ["dollar", "currency", "yen", "yuan", "euro", "fx", "dxy", "usdk rw", "usdkrw"],
    "equity": ["stock", "equity", "shares", "index", "earnings", "nasdaq", "s&p"],
    "sector": ["sector", "banks", "energy stocks", "technology", "healthcare"],
    "crypto": ["bitcoin", "btc", "ether", "ethereum", "stablecoin", "crypto", "token", "exchange hack", "etf"],
    "oil": ["oil", "crude", "brent", "wti", "opec", "refinery", "tanker"],
    "energy": ["lng", "gas", "pipeline", "power", "electricity", "grid"],
    "shipping": ["shipping", "freight", "port", "canal", "strait", "vessel", "container"],
    "supply_chain": ["supply chain", "export controls", "shortage", "semiconductor equipment"],
    "geopolitics": ["war", "conflict", "sanction", "missile", "attack", "border", "military"],
    "defense": ["defense", "missile", "drone", "military", "naval"],
    "semiconductors": ["semiconductor", "chip", "taiwan", "tsmc", "export controls", "lithography"],
    "cyber": ["cyber", "hack", "ransomware", "breach", "malware"],
    "commodities": ["gold", "copper", "wheat", "grain", "commodity"],
    "Korea": ["korea", "north korea", "south korea", "kospi", "seoul"],
}

ASSET_RULES = [
    {
        "keywords": ["iran", "hormuz", "tanker", "sanction", "persian gulf"],
        "assets": [("CL=F", "commodity", "oil/chokepoint exposure"), ("BZ=F", "commodity", "brent oil exposure"), ("XLE", "sector", "energy equity proxy"), ("USO", "commodity_etf", "WTI ETF proxy"), ("BNO", "commodity_etf", "Brent ETF proxy"), ("DXY", "FX", "dollar context"), ("^VIX", "volatility", "risk volatility proxy")],
    },
    {
        "keywords": ["taiwan", "china", "semiconductor", "chip", "tsmc", "export controls"],
        "assets": [("SMH", "sector", "semiconductor ETF proxy"), ("SOXX", "sector", "semiconductor ETF proxy"), ("NVDA", "equity", "AI semiconductor equity"), ("TSM", "equity", "Taiwan semiconductor equity"), ("QQQ", "equity_index", "growth equity proxy"), ("KOSPI", "equity_index", "Korea regional proxy"), ("USDKRW", "FX", "Korea FX proxy")],
    },
    {
        "keywords": ["fed", "inflation", "rates", "treasury", "yield"],
        "assets": [("^TNX", "rates", "US 10Y yield proxy"), ("TLT", "rates_etf", "long-duration bonds"), ("IEF", "rates_etf", "intermediate-duration bonds"), ("SHY", "rates_etf", "short-duration bonds"), ("SPY", "equity_index", "US equity proxy"), ("QQQ", "equity_index", "growth equity proxy"), ("DXY", "FX", "dollar context"), ("GLD", "commodity_etf", "gold proxy")],
    },
    {
        "keywords": ["crypto", "bitcoin", "btc", "ether", "ethereum", "etf", "hack", "stablecoin", "regulation"],
        "assets": [("BTCUSDT", "crypto", "Binance BTC perpetual/spot convention"), ("ETHUSDT", "crypto", "Binance ETH convention"), ("BTC-USD", "crypto", "yfinance BTC proxy"), ("ETH-USD", "crypto", "yfinance ETH proxy"), ("COIN", "equity", "listed crypto venue proxy"), ("MSTR", "equity", "BTC treasury proxy"), ("IBIT", "etf", "spot BTC ETF proxy where available")],
    },
    {
        "keywords": ["korea", "north korea", "south korea", "missile", "seoul"],
        "assets": [("KOSPI", "equity_index", "Korea equity index proxy"), ("EWY", "etf", "Korea ETF proxy"), ("USDKRW", "FX", "Korea FX proxy")],
    },
    {
        "keywords": ["suez", "bab el-mandeb", "red sea", "shipping", "freight", "canal"],
        "assets": [("BDRY", "shipping", "dry bulk freight proxy"), ("CL=F", "commodity", "WTI oil proxy"), ("BZ=F", "commodity", "Brent oil proxy"), ("XLE", "sector", "energy equity proxy")],
    },
]

REGION_ASSETS = {
    "Middle East": [("CL=F", "commodity", "oil exposure"), ("BZ=F", "commodity", "brent oil exposure"), ("XLE", "sector", "energy equity proxy")],
    "Red Sea": [("BDRY", "shipping", "freight proxy"), ("BZ=F", "commodity", "brent oil exposure")],
    "Asia": [("QQQ", "equity_index", "growth equity proxy"), ("SMH", "sector", "semiconductor proxy"), ("DXY", "FX", "dollar context")],
    "Korea": [("KOSPI", "equity_index", "Korea equity proxy"), ("EWY", "etf", "Korea ETF proxy"), ("USDKRW", "FX", "Korea FX proxy")],
    "Europe": [("VGK", "equity_index", "Europe equity proxy"), ("EURUSD=X", "FX", "euro FX proxy"), ("BZ=F", "commodity", "brent oil exposure")],
    "Americas": [("SPY", "equity_index", "US equity proxy"), ("DXY", "FX", "dollar context"), ("^VIX", "volatility", "risk volatility proxy")],
}


def _text(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return " ".join(str(item.get(key, "") or "") for key in ["title", "summary", "description", "region", "country", "domain", "source"])
    return str(item or "")


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return value.to_dict(orient="records")
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return [{"title": str(value)}]


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", _text(text).lower()).strip()


def extract_entities_from_news(item: Any) -> dict[str, list[str]]:
    text = _norm(item)
    entities = {
        "countries": [],
        "regions": [],
        "assets": [],
        "keywords": [],
    }
    country_terms = ["iran", "china", "taiwan", "north korea", "south korea", "korea", "united states", "ukraine", "russia", "israel", "egypt", "panama"]
    region_terms = ["middle east", "red sea", "asia", "europe", "americas", "persian gulf"]
    for term in country_terms:
        if term in text:
            entities["countries"].append(term.title())
    for term in region_terms:
        if term in text:
            entities["regions"].append("Middle East" if term == "persian gulf" else term.title())
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                entities["keywords"].append(keyword)
                if domain not in entities["keywords"]:
                    pass
    for rule in ASSET_RULES:
        if any(keyword in text for keyword in rule["keywords"]):
            entities["assets"].extend(asset for asset, _, _ in rule["assets"])
    entities["assets"] = sorted(set(entities["assets"]))
    entities["keywords"] = sorted(set(entities["keywords"]))
    return entities


def classify_event_domain(item: Any) -> str:
    text = _norm(item)
    scores = {domain: sum(1 for keyword in keywords if keyword in text) for domain, keywords in DOMAIN_KEYWORDS.items()}
    domain, score = max(scores.items(), key=lambda item: item[1])
    return domain if score > 0 else "unknown"


def classify_market_channel(item: Any) -> list[str]:
    domain = classify_event_domain(item)
    channel_map = {
        "macro": ["rates", "FX", "equity"],
        "rates": ["rates", "FX", "equity"],
        "FX": ["FX", "rates"],
        "equity": ["equity"],
        "sector": ["equity", "sector"],
        "crypto": ["crypto", "equity"],
        "oil": ["commodities", "energy", "FX"],
        "energy": ["energy", "commodities"],
        "shipping": ["shipping", "commodities"],
        "supply_chain": ["equity", "sector", "commodities"],
        "geopolitics": ["equity", "FX", "commodities", "volatility"],
        "defense": ["sector", "geopolitics"],
        "semiconductors": ["sector", "equity", "FX"],
        "cyber": ["sector", "equity"],
        "commodities": ["commodities", "FX"],
        "Korea": ["equity", "FX", "geopolitics"],
    }
    return channel_map.get(domain, ["unknown"])


def _asset_payload(ticker: str, asset_class: str, reason: str, score: float, caveat: str = "Related asset mapping is heuristic exposure context.") -> dict[str, Any]:
    return {
        "related_assets": [ticker],
        "related_tickers": [ticker],
        "asset_class": asset_class,
        "relevance_score": max(0, min(100, round(float(score), 1))),
        "reason": reason,
        "caveat": caveat,
    }


def map_keywords_to_assets(item: Any) -> list[dict[str, Any]]:
    text = _norm(item)
    output: dict[str, dict[str, Any]] = {}
    for rule in ASSET_RULES:
        matched = [keyword for keyword in rule["keywords"] if keyword in text]
        if not matched:
            continue
        score = min(100, 55 + len(matched) * 9)
        for ticker, asset_class, reason in rule["assets"]:
            current = output.get(ticker)
            payload = _asset_payload(ticker, asset_class, f"{reason}; matched: {', '.join(matched[:4])}", score)
            if current is None or payload["relevance_score"] > current["relevance_score"]:
                output[ticker] = payload
    return sorted(output.values(), key=lambda row: row["relevance_score"], reverse=True)


def map_region_to_assets(region: str | None) -> list[dict[str, Any]]:
    if not region:
        return []
    rows = []
    for ticker, asset_class, reason in REGION_ASSETS.get(region, []):
        rows.append(_asset_payload(ticker, asset_class, reason, 45, "Regional mapping is a broad exposure proxy."))
    return rows


def map_entities_to_assets(entities: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for region in entities.get("regions", []):
        rows.extend(map_region_to_assets(region))
    for asset in entities.get("assets", []):
        rows.append(_asset_payload(asset, "mapped", "Entity or keyword direct mapping", 70))
    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = row["related_tickers"][0]
        if ticker not in dedup or row["relevance_score"] > dedup[ticker]["relevance_score"]:
            dedup[ticker] = row
    return sorted(dedup.values(), key=lambda row: row["relevance_score"], reverse=True)


def score_asset_relevance(news_item: Any, ticker: str) -> dict[str, Any]:
    related = build_related_asset_list(news_item)
    ticker_upper = str(ticker).upper()
    match = next((row for row in related if ticker_upper in [item.upper() for item in row["related_tickers"]]), None)
    if match:
        return match
    return _asset_payload(ticker_upper, "unknown", "No direct keyword/entity mapping found.", 0, "No relevance claim is made.")


def build_related_asset_list(news_item: Any) -> list[dict[str, Any]]:
    entities = extract_entities_from_news(news_item)
    rows = map_keywords_to_assets(news_item) + map_entities_to_assets(entities)
    for item in _records(news_item):
        region = item.get("region")
        rows.extend(map_region_to_assets(region))
    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = row["related_tickers"][0]
        if ticker not in dedup or row["relevance_score"] > dedup[ticker]["relevance_score"]:
            dedup[ticker] = row
    return sorted(dedup.values(), key=lambda row: row["relevance_score"], reverse=True)
