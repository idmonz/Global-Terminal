from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

from .asset_universe import build_asset_universe_contract
from .event_stream import dedupe_events


GRAPH_CONTRACT_VERSION = "event_asset_graph.v1"

INFERRED_CAVEAT = "Rule-based clean-room inference; verify with provider-backed market data before relying on this link."
PERSISTENCE_CAVEAT = "Live graph persistence is unavailable until a reviewed provider-backed graph or relational store exists."


EVIDENCE_REFS = [
    {
        "external_project": "HelixDB",
        "evidence_ref": "helix-db-main/README.md:5-9",
        "license_stance": "needs-review/mixed",
        "usage": "Graph/query mental model only.",
        "copied_source": False,
        "caveat": "No HelixDB source or query syntax is copied; this contract is first-party JSON.",
    },
    {
        "external_project": "Supabase",
        "evidence_ref": "supabase-master/README.md:9-16",
        "license_stance": "direct-use-allowed",
        "usage": "Future persistence/readiness architecture reference only.",
        "copied_source": False,
        "caveat": "No hosted Supabase auth, database, billing, or client dependency is added in Phase 2F.",
    },
    {
        "external_project": "WorldMonitor",
        "evidence_ref": "Phase 2E WorldMonitor provider-health evidence card",
        "license_stance": "behavior-only",
        "usage": "Provider truth/health behavior reference.",
        "copied_source": False,
        "caveat": "AGPL source stays out of this repository; only the source-status discipline is reused.",
    },
    {
        "external_project": "OpenBB",
        "evidence_ref": "Phase 2E OpenBB router/provider evidence card",
        "license_stance": "behavior-only",
        "usage": "Optional provider/API route mental model.",
        "copied_source": False,
        "caveat": "OpenBB remains optional and user-installed/API-backed; no AGPL source is vendored.",
    },
    {
        "external_project": "FinanceDatabase",
        "evidence_ref": "FinanceDatabase-main/database/equities/NMS.csv:1-1",
        "license_stance": "direct-use-allowed",
        "usage": "Asset-universe schema/taxonomy behavior already adopted in Phase 2E.",
        "copied_source": False,
        "caveat": "External CSV rows are not copied; only schema evidence and taxonomy behavior inform local contracts.",
    },
    {
        "external_project": "BB-Terminal",
        "evidence_ref": "Phase 2E BB-Terminal command-workstation evidence card",
        "license_stance": "blocked",
        "usage": "Clean-room command-workstation behavior reference.",
        "copied_source": False,
        "caveat": "Direct copying remains blocked because refreshed audit did not find a reviewed permissive license file.",
    },
]


COMMAND_LIBRARY = {
    "NI": {
        "label": "News Intelligence",
        "implementation_status": "schema-ready/source-backed-news-required",
        "source_status": "reference-schema",
        "caveat": "Routes from event context to source-backed news rows; not a trading recommendation.",
    },
    "MAP": {
        "label": "War Room Map",
        "implementation_status": "schema-ready/proxy-layer-aware",
        "source_status": "proxy/static",
        "caveat": "Map context may include approximate centroids and static chokepoints.",
    },
    "FXC": {
        "label": "FX Crosses",
        "implementation_status": "schema-ready/provider-required",
        "source_status": "reference-schema",
        "caveat": "FX pair routing is schema-ready; live quotes require provider freshness.",
    },
    "CRYPTO": {
        "label": "Crypto Market",
        "implementation_status": "schema-ready/provider-required",
        "source_status": "reference-schema",
        "caveat": "Crypto routing can use CoinGecko/Binance states when available.",
    },
    "WEI": {
        "label": "Weights / Exposure",
        "implementation_status": "future-provider-required",
        "source_status": "provider-required",
        "caveat": "Constituent, holdings, and exposure rows require provider-backed data.",
    },
    "GP": {
        "label": "Graph / Price",
        "implementation_status": "provider-required",
        "source_status": "provider-required",
        "caveat": "Price graphs require market data freshness and source labels.",
    },
    "HP": {
        "label": "Historical Price",
        "implementation_status": "provider-required",
        "source_status": "provider-required",
        "caveat": "Historical price context requires a configured or keyless market provider.",
    },
    "DES": {
        "label": "Description",
        "implementation_status": "schema-ready/provider-required",
        "source_status": "reference-schema",
        "caveat": "Security descriptions require provider-backed asset rows before live claims.",
    },
}


THEME_RULES = [
    {
        "rule_id": "shipping_energy_chokepoint",
        "keywords": ["red sea", "bab el-mandeb", "suez", "hormuz", "shipping", "tanker", "chokepoint", "vessel", "freight"],
        "risk_themes": [("energy_chokepoint", "Energy Chokepoint"), ("global_trade", "Global Trade")],
        "sectors": [("energy", "Energy"), ("shipping_logistics", "Shipping / Logistics")],
        "commodities": [("wti-crude", "WTI Crude"), ("brent-crude", "Brent Crude")],
        "fx_pairs": [("usdjpy", "USD/JPY"), ("eurusd", "EUR/USD")],
        "crypto_pairs": [("btcusd", "BTC/USD")],
        "commands": ["NI", "MAP", "FXC", "WEI", "GP"],
        "confidence": 0.62,
        "caveat": "Shipping and energy links are macro transmission channels; no live vessel-flow telemetry is claimed.",
    },
    {
        "rule_id": "crypto_market",
        "keywords": ["crypto", "bitcoin", "btc", "ether", "ethereum", "eth", "stablecoin", "binance", "coingecko"],
        "risk_themes": [("crypto_liquidity", "Crypto Liquidity")],
        "sectors": [("digital_assets", "Digital Assets")],
        "commodities": [],
        "fx_pairs": [("usdjpy", "USD/JPY")],
        "crypto_pairs": [("btcusd", "BTC/USD"), ("ethusd", "ETH/USD")],
        "commands": ["NI", "CRYPTO", "GP", "HP"],
        "confidence": 0.68,
        "caveat": "Crypto links use public/provider-status context and remain non-advisory.",
    },
    {
        "rule_id": "macro_rates_fx",
        "keywords": ["fed", "rates", "treasury", "yield", "inflation", "dollar", "dxy", "currency", "fx"],
        "risk_themes": [("macro_rates", "Macro Rates"), ("fx_risk", "FX Risk")],
        "sectors": [("financials", "Financials")],
        "commodities": [("gold", "Gold")],
        "fx_pairs": [("usdjpy", "USD/JPY"), ("eurusd", "EUR/USD")],
        "crypto_pairs": [("btcusd", "BTC/USD")],
        "commands": ["NI", "FXC", "GP", "HP"],
        "confidence": 0.58,
        "caveat": "Macro/FX relationships are heuristic exposure routes unless backed by fresh provider data.",
    },
    {
        "rule_id": "natural_disaster",
        "keywords": ["earthquake", "usgs", "storm", "wildfire", "weather", "natural"],
        "risk_themes": [("natural_hazard", "Natural Hazard")],
        "sectors": [("insurance", "Insurance"), ("utilities", "Utilities")],
        "commodities": [],
        "fx_pairs": [("usdjpy", "USD/JPY")],
        "crypto_pairs": [],
        "commands": ["NI", "MAP"],
        "confidence": 0.52,
        "caveat": "Natural-risk market links are contextual until local market and supply-chain providers are wired.",
    },
]


TICKER_LINKS = {
    "CL=F": {"type": "commodity", "id": "wti-crude", "label": "WTI Crude", "commands": ["GP", "HP"]},
    "WTI": {"type": "commodity", "id": "wti-crude", "label": "WTI Crude", "commands": ["GP", "HP"]},
    "BZ=F": {"type": "commodity", "id": "brent-crude", "label": "Brent Crude", "commands": ["GP", "HP"]},
    "BRENT": {"type": "commodity", "id": "brent-crude", "label": "Brent Crude", "commands": ["GP", "HP"]},
    "DXY": {"type": "fx_pair", "id": "usd-risk-basket", "label": "USD Risk Basket", "commands": ["FXC", "GP"]},
    "BTC": {"type": "crypto_pair", "id": "btcusd", "label": "BTC/USD", "commands": ["CRYPTO", "GP", "HP"]},
    "BTCUSDT": {"type": "crypto_pair", "id": "btcusd", "label": "BTC/USD", "commands": ["CRYPTO", "GP", "HP"]},
    "ETH": {"type": "crypto_pair", "id": "ethusd", "label": "ETH/USD", "commands": ["CRYPTO", "GP", "HP"]},
    "ETHUSDT": {"type": "crypto_pair", "id": "ethusd", "label": "ETH/USD", "commands": ["CRYPTO", "GP", "HP"]},
    "SPX": {"type": "index", "id": "spx", "label": "S&P 500", "commands": ["GP", "HP", "WEI"]},
    "NDX": {"type": "index", "id": "ndx", "label": "Nasdaq 100", "commands": ["GP", "HP", "WEI"]},
    "XLE": {"type": "sector", "id": "energy", "label": "Energy", "commands": ["GP", "WEI"]},
    "BDRY": {"type": "sector", "id": "shipping_logistics", "label": "Shipping / Logistics", "commands": ["GP", "WEI"]},
}


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return [dict(item) for item in value.to_dict(orient="records")]
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        if "ledger" in value and isinstance(value["ledger"], list):
            return _records(value["ledger"])
        return [dict(value)]
    return []


def _slug(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "-", text)
    return text.strip("-_") or "unknown"


def _node_id(node_type: str, value: Any) -> str:
    if node_type == "command":
        return f"command:{str(value or 'UNKNOWN').strip().upper()}"
    return f"{node_type}:{_slug(value)}"


def _edge_id(source: str, target: str, relationship: str) -> str:
    seed = f"{source}|{target}|{relationship}"
    return f"edge:{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:14]}"


def _text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in ["title", "summary", "description", "domain", "region", "source", "related_tickers", "related_assets"]
    ).lower()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _confidence(value: Any, fallback: float = 0.5) -> float:
    try:
        number = float(value)
        if number > 1:
            number = number / 100.0
        return round(max(0.05, min(0.99, number)), 2)
    except Exception:
        return fallback


def _source_status(row: dict[str, Any], fallback: str = "unknown") -> str:
    return str(row.get("source_status") or row.get("freshness_status") or row.get("freshness") or row.get("status") or fallback)


def _event_identifier(row: dict[str, Any]) -> str:
    if row.get("event_id"):
        return str(row["event_id"])
    seed = "|".join(str(row.get(key, "")) for key in ["timestamp", "title", "source", "region", "domain"])
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _node(
    node_id: str,
    node_type: str,
    label: str,
    *,
    source_status: str,
    confidence: float,
    provider: str = "",
    source_url: str = "",
    fetched_at: str | None = None,
    caveat: str = "",
    data_gap: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "source_status": source_status,
        "confidence": round(float(confidence), 2),
        "provider": provider,
        "source_url": source_url,
        "fetched_at": fetched_at,
        "caveat": caveat,
        "data_gap": data_gap,
        "metadata": metadata or {},
    }


def _edge(
    source: str,
    target: str,
    relationship: str,
    *,
    confidence: float,
    source_status: str,
    evidence: str,
    caveat: str = "",
    provider: str = "",
    source_url: str = "",
    fetched_at: str | None = None,
) -> dict[str, Any]:
    return {
        "id": _edge_id(source, target, relationship),
        "source": source,
        "target": target,
        "relationship": relationship,
        "confidence": round(float(confidence), 2),
        "source_status": source_status,
        "evidence": evidence,
        "caveat": caveat,
        "provider": provider,
        "source_url": source_url,
        "fetched_at": fetched_at,
    }


def _add_node(nodes: dict[str, dict[str, Any]], node: dict[str, Any]) -> None:
    existing = nodes.get(node["id"])
    if existing is None or float(node.get("confidence") or 0) > float(existing.get("confidence") or 0):
        nodes[node["id"]] = node


def _add_edge(edges: dict[str, dict[str, Any]], edge: dict[str, Any]) -> None:
    existing = edges.get(edge["id"])
    if existing is None or float(edge.get("confidence") or 0) > float(existing.get("confidence") or 0):
        edges[edge["id"]] = edge


def _event_node(row: dict[str, Any]) -> dict[str, Any]:
    event_id = _event_identifier(row)
    return _node(
        f"event:{event_id}",
        "event",
        str(row.get("title") or "Untitled event"),
        source_status=_source_status(row),
        confidence=_confidence(row.get("confidence"), 0.5),
        provider=str(row.get("provider") or ""),
        source_url=str(row.get("source_url") or row.get("url") or ""),
        fetched_at=str(row.get("fetched_at")) if row.get("fetched_at") else None,
        caveat=str(row.get("caveat") or "Source-backed event row; inspect caveats and source freshness."),
        data_gap=str(row.get("data_gap") or ""),
        metadata={
            "event_id": event_id,
            "timestamp": row.get("timestamp"),
            "severity": row.get("severity"),
            "domain": row.get("domain"),
            "region": row.get("region"),
            "source": row.get("source"),
            "related_tickers": _as_list(row.get("related_tickers")),
        },
    )


def _add_reference_asset_nodes(nodes: dict[str, dict[str, Any]], edges: dict[str, dict[str, Any]]) -> None:
    contract = build_asset_universe_contract()
    for asset in contract.get("asset_classes", []):
        asset_id = _node_id("asset_class", asset.get("asset_class"))
        _add_node(
            nodes,
            _node(
                asset_id,
                "asset_class",
                str(asset.get("label") or asset.get("asset_class")),
                source_status=str(asset.get("source_status") or "reference-schema"),
                confidence=0.72,
                provider="phase2e_native_contract",
                source_url=str(asset.get("evidence_ref") or ""),
                fetched_at=None,
                caveat=str(asset.get("caveat") or "Phase 2E reference schema; no live rows claimed."),
                data_gap="No provider-backed live universe rows are bundled in this slice.",
                metadata={
                    "asset_class": asset.get("asset_class"),
                    "primary_identifier": asset.get("primary_identifier"),
                    "routing_commands": asset.get("routing_commands") or [],
                    "live_rows_claimed": bool(asset.get("live_rows_claimed")),
                    "license_stance": asset.get("license_stance"),
                },
            ),
        )
        for command in asset.get("routing_commands") or []:
            command_id = _node_id("command", command)
            _add_command_node(nodes, str(command))
            _add_edge(
                edges,
                _edge(
                    asset_id,
                    command_id,
                    "routes_to",
                    confidence=0.7,
                    source_status="reference-schema",
                    evidence=f"Phase 2E command matrix maps {asset.get('asset_class')} to {command}.",
                    caveat="Routing readiness does not imply live provider data.",
                    provider="phase2e_native_contract",
                ),
            )
    _add_node(
        nodes,
        _node(
            "asset_class:commodity",
            "asset_class",
            "Commodities",
            source_status="schema-gap/proxy",
            confidence=0.45,
            provider="phase2f_native_contract",
            caveat="Phase 2E asset-universe schema does not yet include a commodity universe; commodity nodes are first-party proxy classifications.",
            data_gap="Provider-backed commodity reference rows remain future work.",
            metadata={"asset_class": "commodity", "live_rows_claimed": False},
        ),
    )


def _add_command_node(nodes: dict[str, dict[str, Any]], command: str) -> None:
    definition = COMMAND_LIBRARY.get(command, {})
    _add_node(
        nodes,
        _node(
            _node_id("command", command),
            "command",
            str(definition.get("label") or command),
            source_status=str(definition.get("source_status") or "reference-schema"),
            confidence=0.66,
            provider="phase2f_native_contract",
            caveat=str(definition.get("caveat") or "Clean-room command routing only."),
            data_gap="Live command execution depends on the destination provider and payload freshness.",
            metadata={"command": command, "implementation_status": definition.get("implementation_status", "schema-ready")},
        ),
    )


def _add_provider_nodes(nodes: dict[str, dict[str, Any]], provider_rows: list[dict[str, Any]]) -> None:
    for row in provider_rows:
        provider = str(row.get("provider") or row.get("source") or "unknown_provider")
        status = _source_status(row, "unavailable")
        _add_node(
            nodes,
            _node(
                _node_id("provider", provider),
                "provider",
                provider,
                source_status=status,
                confidence=0.95 if status in {"live/fresh", "cached", "fixture"} else 0.5,
                provider=provider,
                source_url=str(row.get("source_url") or row.get("source") or ""),
                fetched_at=str(row.get("fetched_at")) if row.get("fetched_at") else None,
                caveat=str(row.get("caveat") or row.get("warning") or ""),
                data_gap=str(row.get("error") or ""),
                metadata={
                    "availability": row.get("availability"),
                    "row_count": row.get("row_count"),
                    "recommended_action": row.get("recommended_action"),
                },
            ),
        )


def _matching_rules(row: dict[str, Any]) -> list[dict[str, Any]]:
    text = _text(row)
    matches = [rule for rule in THEME_RULES if any(keyword in text for keyword in rule["keywords"])]
    domain = str(row.get("domain") or "").lower()
    if domain in {"chokepoints", "shipping", "energy"} and not any(rule["rule_id"] == "shipping_energy_chokepoint" for rule in matches):
        matches.append(THEME_RULES[0])
    if domain == "crypto" and not any(rule["rule_id"] == "crypto_market" for rule in matches):
        matches.append(THEME_RULES[1])
    if domain == "natural" and not any(rule["rule_id"] == "natural_disaster" for rule in matches):
        matches.append(THEME_RULES[3])
    return matches or [
        {
            "rule_id": "generic_news_context",
            "keywords": [],
            "risk_themes": [("market_context", "Market Context")],
            "sectors": [],
            "commodities": [],
            "fx_pairs": [],
            "crypto_pairs": [],
            "commands": ["NI", "MAP"],
            "confidence": 0.42,
            "caveat": "Generic event context only; no specific cross-asset relationship was inferred.",
        }
    ]


def _add_typed_market_node(
    nodes: dict[str, dict[str, Any]],
    node_type: str,
    value: str,
    label: str,
    *,
    confidence: float,
    caveat: str,
) -> str:
    node_id = _node_id(node_type, value)
    source_status = "inferred/proxy"
    asset_class_target = {
        "commodity": "asset_class:commodity",
        "fx_pair": "asset_class:fx_pair",
        "crypto_pair": "asset_class:crypto_pair",
        "sector": None,
        "risk_theme": None,
        "index": "asset_class:index",
    }.get(node_type)
    _add_node(
        nodes,
        _node(
            node_id,
            node_type,
            label,
            source_status=source_status,
            confidence=confidence,
            provider="phase2f_rule_map",
            caveat=caveat,
            data_gap="Relationship is inferred from event text and static taxonomy.",
            metadata={"asset_class_node": asset_class_target},
        ),
    )
    return node_id


def _connect_to_asset_class(
    edges: dict[str, dict[str, Any]],
    source_node: str,
    market_type: str,
    *,
    confidence: float,
    evidence: str,
) -> None:
    target = {
        "commodity": "asset_class:commodity",
        "fx_pair": "asset_class:fx_pair",
        "crypto_pair": "asset_class:crypto_pair",
        "index": "asset_class:index",
    }.get(market_type)
    if not target:
        return
    _add_edge(
        edges,
        _edge(
            source_node,
            target,
            "proxy_for",
            confidence=min(confidence, 0.58),
            source_status="inferred/proxy",
            evidence=evidence,
            caveat=INFERRED_CAVEAT,
            provider="phase2f_rule_map",
        ),
    )


def _add_event_relationships(
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, dict[str, Any]],
    row: dict[str, Any],
) -> None:
    event_node = _event_node(row)
    event_id = event_node["id"]
    _add_node(nodes, event_node)

    status = _source_status(row)
    confidence = _confidence(row.get("confidence"), 0.5)
    provider = str(row.get("provider") or "")
    source_url = str(row.get("source_url") or row.get("url") or "")
    fetched_at = str(row.get("fetched_at")) if row.get("fetched_at") else None
    title = str(row.get("title") or "Untitled event")

    region = str(row.get("region") or "Global")
    region_id = _node_id("region", region)
    _add_node(
        nodes,
        _node(
            region_id,
            "region",
            region,
            source_status=status,
            confidence=confidence,
            provider=provider,
            source_url=source_url,
            fetched_at=fetched_at,
            caveat="Region comes from source row, normalized event metadata, or approximate centroid logic.",
            data_gap="Precise coordinates may be absent or approximate.",
        ),
    )
    _add_edge(
        edges,
        _edge(
            event_id,
            region_id,
            "located_in",
            confidence=confidence,
            source_status=status,
            evidence=f"Event region field: {region}.",
            caveat=str(row.get("caveat") or ""),
            provider=provider,
            source_url=source_url,
            fetched_at=fetched_at,
        ),
    )

    if provider:
        provider_id = _node_id("provider", provider)
        _add_node(
            nodes,
            _node(
                provider_id,
                "provider",
                provider,
                source_status=status,
                confidence=confidence,
                provider=provider,
                source_url=source_url,
                fetched_at=fetched_at,
                caveat="Provider attached to the source event row.",
                data_gap=str(row.get("data_gap") or ""),
            ),
        )
        _add_edge(
            edges,
            _edge(
                event_id,
                provider_id,
                "reported_by",
                confidence=confidence,
                source_status=status,
                evidence=f"Event provider/source: {provider}.",
                caveat="Provider status must be read with freshness and caveats.",
                provider=provider,
                source_url=source_url,
                fetched_at=fetched_at,
            ),
        )

    commands: set[str] = {"NI"}
    for rule in _matching_rules(row):
        rule_confidence = min(confidence, float(rule["confidence"]))
        for theme_id, theme_label in rule["risk_themes"]:
            target = _add_typed_market_node(
                nodes,
                "risk_theme",
                theme_id,
                theme_label,
                confidence=rule_confidence,
                caveat=str(rule["caveat"]),
            )
            _add_edge(
                edges,
                _edge(
                    event_id,
                    target,
                    "mentions",
                    confidence=rule_confidence,
                    source_status="inferred/proxy",
                    evidence=f"Rule {rule['rule_id']} matched event text: {title}",
                    caveat=str(rule["caveat"]),
                    provider="phase2f_rule_map",
                ),
            )
        for sector_id, sector_label in rule["sectors"]:
            target = _add_typed_market_node(
                nodes,
                "sector",
                sector_id,
                sector_label,
                confidence=rule_confidence,
                caveat=str(rule["caveat"]),
            )
            _add_edge(
                edges,
                _edge(
                    event_id,
                    target,
                    "affects",
                    confidence=rule_confidence,
                    source_status="inferred/proxy",
                    evidence=f"Rule {rule['rule_id']} maps event to sector {sector_label}.",
                    caveat=str(rule["caveat"]),
                    provider="phase2f_rule_map",
                ),
            )
        for commodity_id, commodity_label in rule["commodities"]:
            target = _add_typed_market_node(
                nodes,
                "commodity",
                commodity_id,
                commodity_label,
                confidence=rule_confidence,
                caveat=str(rule["caveat"]),
            )
            _add_edge(
                edges,
                _edge(
                    event_id,
                    target,
                    "affects",
                    confidence=rule_confidence,
                    source_status="inferred/proxy",
                    evidence=f"Rule {rule['rule_id']} maps event to commodity {commodity_label}.",
                    caveat=str(rule["caveat"]),
                    provider="phase2f_rule_map",
                ),
            )
            _connect_to_asset_class(edges, target, "commodity", confidence=rule_confidence, evidence=f"{commodity_label} is grouped under the Phase 2F commodity proxy asset class.")
        for fx_id, fx_label in rule["fx_pairs"]:
            target = _add_typed_market_node(
                nodes,
                "fx_pair",
                fx_id,
                fx_label,
                confidence=rule_confidence,
                caveat=str(rule["caveat"]),
            )
            _add_edge(
                edges,
                _edge(
                    event_id,
                    target,
                    "affects",
                    confidence=rule_confidence,
                    source_status="inferred/proxy",
                    evidence=f"Rule {rule['rule_id']} maps event to FX pair {fx_label}.",
                    caveat=str(rule["caveat"]),
                    provider="phase2f_rule_map",
                ),
            )
            _connect_to_asset_class(edges, target, "fx_pair", confidence=rule_confidence, evidence=f"{fx_label} uses the Phase 2E FX-pair schema.")
        for crypto_id, crypto_label in rule["crypto_pairs"]:
            target = _add_typed_market_node(
                nodes,
                "crypto_pair",
                crypto_id,
                crypto_label,
                confidence=min(rule_confidence, 0.48) if rule["rule_id"] != "crypto_market" else rule_confidence,
                caveat=str(rule["caveat"]),
            )
            _add_edge(
                edges,
                _edge(
                    event_id,
                    target,
                    "affects",
                    confidence=min(rule_confidence, 0.48) if rule["rule_id"] != "crypto_market" else rule_confidence,
                    source_status="inferred/proxy",
                    evidence=f"Rule {rule['rule_id']} maps event to crypto pair {crypto_label}.",
                    caveat=str(rule["caveat"]),
                    provider="phase2f_rule_map",
                ),
            )
            _connect_to_asset_class(edges, target, "crypto_pair", confidence=rule_confidence, evidence=f"{crypto_label} uses the Phase 2E crypto-pair schema.")
        commands.update(str(command) for command in rule["commands"])

    for ticker in _as_list(row.get("related_tickers") or row.get("related_assets")):
        link = TICKER_LINKS.get(ticker.upper())
        if not link:
            continue
        target_type = str(link["type"])
        target = _add_typed_market_node(
            nodes,
            target_type,
            str(link["id"]),
            str(link["label"]),
            confidence=min(confidence, 0.7),
            caveat="Related ticker supplied by the event row; mapped through first-party Phase 2F ticker rules.",
        )
        _add_edge(
            edges,
            _edge(
                event_id,
                target,
                "mentions",
                confidence=min(confidence, 0.7),
                source_status="inferred/proxy",
                evidence=f"Event related_tickers includes {ticker}.",
                caveat=INFERRED_CAVEAT,
                provider="phase2f_rule_map",
            ),
        )
        _connect_to_asset_class(edges, target, target_type, confidence=min(confidence, 0.7), evidence=f"{ticker} maps to {link['label']} through local ticker rules.")
        commands.update(str(command) for command in link.get("commands", []))

    for command in sorted(commands):
        command_id = _node_id("command", command)
        _add_command_node(nodes, command)
        _add_edge(
            edges,
            _edge(
                event_id,
                command_id,
                "routes_to",
                confidence=min(confidence, 0.72),
                source_status="reference-schema" if command == "NI" else "inferred/proxy",
                evidence=f"Command {command} suggested from event graph context.",
                caveat=COMMAND_LIBRARY.get(command, {}).get("caveat", "Clean-room command routing only."),
                provider="phase2f_native_contract",
            ),
        )


def _build_clusters(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    connected_by_target: dict[str, set[str]] = {}
    for edge in edges:
        connected_by_target.setdefault(str(edge["target"]), set()).add(str(edge["source"]))
    clusters = []
    for node in nodes:
        if node["type"] not in {"region", "risk_theme", "asset_class"}:
            continue
        event_ids = sorted(source for source in connected_by_target.get(node["id"], set()) if source.startswith("event:"))
        clusters.append(
            {
                "cluster_id": f"cluster:{node['id']}",
                "type": node["type"],
                "label": node["label"],
                "node_id": node["id"],
                "event_count": len(event_ids),
                "event_node_ids": event_ids,
                "source_status": node["source_status"],
                "caveat": node["caveat"],
            }
        )
    return sorted(clusters, key=lambda item: (item["type"], item["label"]))


def _build_command_suggestions(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions = []
    command_nodes = {node["id"]: node for node in nodes if node["type"] == "command"}
    for command_id, node in sorted(command_nodes.items()):
        inbound = [edge for edge in edges if edge["target"] == command_id and edge["relationship"] == "routes_to"]
        event_ids = sorted({edge["source"] for edge in inbound if str(edge["source"]).startswith("event:")})
        if not inbound and not event_ids:
            continue
        command = str(node.get("metadata", {}).get("command") or node["label"])
        definition = COMMAND_LIBRARY.get(command, {})
        suggestions.append(
            {
                "command": command,
                "label": node["label"],
                "target_node_id": command_id,
                "related_event_node_ids": event_ids,
                "relationship_count": len(inbound),
                "confidence": round(max((float(edge["confidence"]) for edge in inbound), default=float(node["confidence"])), 2),
                "source_status": node["source_status"],
                "implementation_status": definition.get("implementation_status", node.get("metadata", {}).get("implementation_status")),
                "caveat": definition.get("caveat") or node["caveat"],
            }
        )
    return suggestions


def _readiness() -> dict[str, Any]:
    unavailable = [
        {
            "capability": "live_graph_persistence",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Review and wire a provider-backed graph or relational store before enabling persistence.",
            "caveat": PERSISTENCE_CAVEAT,
        },
        {
            "capability": "user_specific_watchlist_graph_state",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Add authenticated persistence in a later commercial slice.",
            "caveat": "No accounts, auth, billing, or hosted database are added in Phase 2F.",
        },
    ]
    return {
        "graph_persistence": unavailable[0],
        "live_store": {
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "caveat": PERSISTENCE_CAVEAT,
        },
        "provider_requirements": [
            "Reviewed provider-backed graph or relational store.",
            "Source-level provenance and freshness metadata for every persisted row.",
            "Explicit retention, auth, and privacy review before user-specific graph state.",
        ],
        "graph_database_dependency_added": False,
        "hosted_supabase_dependency_added": False,
        "unavailable_capabilities": unavailable,
    }


def build_event_asset_graph_contract(
    *,
    events: Any = None,
    provider_rows: Any = None,
    asset_universe: dict[str, Any] | None = None,
    max_events: int = 40,
) -> dict[str, Any]:
    """Build a deterministic clean-room event-to-asset graph contract."""
    if events is None:
        from .war_room import build_war_room_state

        events = build_war_room_state(include_default_runtime=False).get("events")
    event_rows = dedupe_events(_records(events))[:max_events]
    provider_status_rows = _records(provider_rows)
    if asset_universe is not None:
        asset_contract = asset_universe
    else:
        asset_contract = build_asset_universe_contract()

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    _add_reference_asset_nodes(nodes, edges)
    _add_provider_nodes(nodes, provider_status_rows)

    for row in event_rows:
        _add_event_relationships(nodes, edges, row)

    node_list = sorted(nodes.values(), key=lambda item: (item["type"], item["id"]))
    edge_list = sorted(edges.values(), key=lambda item: item["id"])
    clusters = _build_clusters(node_list, edge_list)
    command_suggestions = _build_command_suggestions(node_list, edge_list)
    inferred_edges = [edge for edge in edge_list if edge["source_status"] == "inferred/proxy"]
    source_backed_edges = [edge for edge in edge_list if edge["source_status"] not in {"inferred/proxy", "reference-schema"}]
    readiness = _readiness()

    return {
        "graph_contract_version": GRAPH_CONTRACT_VERSION,
        "nodes": node_list,
        "edges": edge_list,
        "clusters": clusters,
        "command_suggestions": command_suggestions,
        "readiness": readiness,
        "evidence_refs": EVIDENCE_REFS,
        "asset_universe_readiness": asset_contract.get("readiness", {}),
        "summary": {
            "node_count": len(node_list),
            "edge_count": len(edge_list),
            "event_node_count": sum(1 for node in node_list if node["type"] == "event"),
            "inferred_edge_count": len(inferred_edges),
            "source_backed_edge_count": len(source_backed_edges),
            "command_count": len(command_suggestions),
            "cluster_count": len(clusters),
            "persistence_status": readiness["graph_persistence"]["status"],
            "live_graph_persistence": False,
            "asset_schema_mode": asset_contract.get("readiness", {}).get("default_mode", "reference-schema"),
            "external_rows_copied": False,
        },
    }
