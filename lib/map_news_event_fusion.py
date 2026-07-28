from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


MAP_NEWS_EVENT_FUSION_VERSION = "map_news_event_fusion.v2"

LIVE_STATUSES = {"live/fresh", "fresh", "cached", "stale"}
BROAD_REGIONS = {"global", "americas", "europe", "asia", "africa", "oceania", "pacific", "middle east", "antarctic"}
DOMAIN_NEWS_TERMS = {
    "chokepoints": {"shipping", "ship", "tanker", "freight", "canal", "strait", "oil", "gas", "energy", "port"},
    "shipping": {"shipping", "ship", "tanker", "freight", "canal", "strait", "port"},
    "energy": {"oil", "gas", "energy", "pipeline", "refinery", "lng"},
    "natural": {"earthquake", "seismic", "wildfire", "storm", "hurricane", "flood", "volcano"},
    "geopolitical": {"conflict", "sanction", "missile", "war", "diplomatic", "border"},
    "crypto": {"bitcoin", "crypto", "ethereum", "stablecoin", "exchange"},
    "market": {"stocks", "equity", "rates", "treasury", "inflation", "central bank"},
}
LOGISTICS_NEWS_TERMS = {"shipping", "ship", "tanker", "freight", "canal", "strait", "port"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return []


def _data(value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    inner = value.get("data")
    return inner if isinstance(inner, dict) else value


def _status(value: dict[str, Any], *keys: str, default: str = "unknown") -> str:
    for key in keys:
        item = value.get(key)
        if item not in {None, ""}:
            return str(item)
    return default


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _source_row(row: dict[str, Any], *, fallback_provider: str, fallback_source: str) -> dict[str, Any]:
    return {
        "provider": row.get("provider") or fallback_provider,
        "source": row.get("source") or row.get("source_url") or fallback_source,
        "source_url": row.get("source_url") or row.get("url") or "",
        "source_status": _status(row, "source_status", "freshness", "status"),
        "freshness": _status(row, "freshness", "freshness_status", "source_status"),
        "fetched_at": row.get("fetched_at") or row.get("latest_fetched_at") or row.get("published_at"),
        "confidence": row.get("confidence"),
        "caveat": row.get("caveat") or "",
        "data_gap": row.get("data_gap") or "",
    }


def _select_marker(markers: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not markers:
        return None
    return sorted(
        markers,
        key=lambda row: (
            -_as_float(row.get("severity_score")),
            -_as_float(row.get("confidence")),
            str(row.get("title") or ""),
        ),
    )[0]


def _news_match(news: dict[str, Any], marker: dict[str, Any]) -> tuple[str, int] | None:
    if not marker:
        return None
    marker_title = _norm(marker.get("title"))
    marker_region = _norm(marker.get("region"))
    marker_url = _norm(marker.get("source_url") or marker.get("url"))
    news_title = _norm(news.get("title"))
    news_text = f"{news_title} {_norm(news.get('summary') or news.get('description'))}"
    news_region = _norm(news.get("region") or news.get("location"))
    news_url = _norm(news.get("source_url") or news.get("url"))
    if marker_url and news_url and marker_url == news_url:
        return "source-url", 100
    if marker_title and news_title and (marker_title in news_title or news_title in marker_title):
        return "title", 90
    if (
        marker_region
        and marker_region not in BROAD_REGIONS | {"unknown", "none"}
        and _norm(marker.get("region_method")) != "coordinate-derived-broad-region"
        and marker_region == news_region
    ):
        return "region", 70
    marker_domain = _norm(marker.get("domain"))
    domain_terms = DOMAIN_NEWS_TERMS.get(marker_domain, set())
    domain_hits = sum(1 for term in domain_terms if re.search(rf"\b{re.escape(term)}\b", news_text))
    logistics_hit = any(re.search(rf"\b{re.escape(term)}\b", news_text) for term in LOGISTICS_NEWS_TERMS)
    if marker_domain in {"chokepoints", "shipping"} and logistics_hit:
        return "domain-keyword", 45
    if marker_domain not in {"chokepoints", "shipping"} and domain_hits >= 2:
        return "domain-keyword", 45
    return None


def _news_identity(row: dict[str, Any]) -> str:
    return _norm(row.get("source_url") or row.get("url")) or "|".join(
        [_norm(row.get("provider")), _norm(row.get("title")), _norm(row.get("published_at"))]
    )


def _combined_news_rows(news_data: dict[str, Any], limit: int = 80) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for collection in [
        _records(news_data.get("normalized_news")),
        _records(news_data.get("high_severity_feed")),
        _records(news_data.get("event_rows")),
    ]:
        for row in collection:
            identity = _news_identity(row)
            if not identity or identity in seen:
                continue
            seen.add(identity)
            output.append(row)
            if len(output) >= limit:
                return output
    return output


def _dedupe_unavailable_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (
            _norm(row.get("provider") or row.get("source")),
            _norm(row.get("layer_id") or row.get("source")),
            _norm(row.get("status") or row.get("source_status") or row.get("availability")),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def _related_news_rows(news_rows: list[dict[str, Any]], marker: dict[str, Any], limit: int = 6) -> list[dict[str, Any]]:
    matches: list[tuple[int, dict[str, Any]]] = []
    for news in news_rows:
        match = _news_match(news, marker)
        if not match:
            continue
        method, score = match
        matches.append(
            (
                score,
                {
                    **news,
                    "match_method": method,
                    "match_score": score,
                    "match_caveat": "Context match only; co-location or topic overlap is not proof of causality.",
                    "not_financial_advice": True,
                },
            )
        )
    return [row for _, row in sorted(matches, key=lambda item: (-item[0], str(item[1].get("title") or "")))[:limit]]


def _node_lookup(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(node.get("id")): node for node in nodes if node.get("id")}


def _event_link_rows(
    *,
    marker: dict[str, Any] | None,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    limit: int = 24,
) -> list[dict[str, Any]]:
    if not marker:
        return []
    node_by_id = _node_lookup(nodes)
    event_node_id = str(marker.get("event_graph_node_id") or "")
    if not event_node_id:
        return []
    rows: list[dict[str, Any]] = []
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if event_node_id not in {source, target}:
            continue
        other_id = target if source == event_node_id else source
        other = node_by_id.get(other_id, {})
        if other.get("type") == "event":
            continue
        rows.append(
            {
                "edge_id": edge.get("id"),
                "source": source,
                "target": target,
                "relationship": edge.get("relationship"),
                "label": other.get("label") or other_id,
                "node_type": other.get("type"),
                "provider": edge.get("provider") or other.get("provider") or "event_asset_graph",
                "source_status": edge.get("source_status") or other.get("source_status") or "unknown",
                "confidence": edge.get("confidence") or other.get("confidence"),
                "fetched_at": edge.get("fetched_at") or other.get("fetched_at"),
                "caveat": edge.get("caveat") or other.get("caveat") or "",
                "data_gap": edge.get("data_gap") or other.get("data_gap") or "",
                "not_financial_advice": True,
            }
        )
    return rows[:limit]


def _event_context(
    *,
    marker: dict[str, Any],
    news_rows: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    heatmap_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    related_news = _related_news_rows(news_rows, marker)
    event_links = _event_link_rows(marker=marker, nodes=nodes, edges=edges)
    connected_assets = _connected_assets(marker=marker, nodes=nodes, heatmap_rows=heatmap_rows)
    heatmap_context = _heatmap_context(marker, heatmap_rows, limit=6)
    source_status = _norm(marker.get("source_status"))
    source_bonus = 12 if source_status in LIVE_STATUSES else 3 if "proxy" in source_status or "fixture" in source_status else 0
    score = min(
        100,
        round(
            source_bonus
            + _as_float(marker.get("severity_score")) * 0.18
            + len(related_news) * 7
            + len(connected_assets) * 3
            + len(event_links) * 1.5
        ),
    )
    if related_news:
        context_status = "source-linked"
    elif connected_assets or event_links:
        context_status = "taxonomy-linked"
    else:
        context_status = "event-only"
    return {
        "marker_id": marker.get("marker_id"),
        "event_id": marker.get("event_id"),
        "event_graph_node_id": marker.get("event_graph_node_id"),
        "context_status": context_status,
        "context_score": score,
        "related_news": related_news,
        "event_links": event_links,
        "connected_assets": connected_assets,
        "heatmap_context": heatmap_context,
        "source_status": marker.get("source_status"),
        "provider": marker.get("provider"),
        "fetched_at": marker.get("fetched_at"),
        "caveat": "News matches are contextual; taxonomy links are inferred/proxy unless their own row says otherwise.",
        "data_gap": "No relationship is promoted to causal evidence without a direct source match.",
        "not_financial_advice": True,
    }


def _connected_assets(
    *,
    marker: dict[str, Any] | None,
    nodes: list[dict[str, Any]],
    heatmap_rows: list[dict[str, Any]],
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not marker:
        return []
    node_by_id = _node_lookup(nodes)
    related_ids = [str(item) for item in _list(marker.get("related_asset_node_ids"))]
    rows: list[dict[str, Any]] = []
    for node_id in related_ids:
        node = node_by_id.get(node_id)
        if not node:
            continue
        rows.append(
            {
                "id": node_id,
                "label": node.get("label"),
                "type": node.get("type"),
                "provider": node.get("provider"),
                "source_status": node.get("source_status"),
                "confidence": node.get("confidence"),
                "fetched_at": node.get("fetched_at"),
                "caveat": node.get("caveat"),
                "data_gap": node.get("data_gap"),
                "not_financial_advice": True,
            }
        )
    marker_terms = " ".join([str(marker.get("title") or ""), str(marker.get("summary") or ""), " ".join(related_ids)]).lower()
    for row in heatmap_rows:
        sector = _norm(row.get("sector"))
        symbol = _norm(row.get("symbol"))
        if sector and sector.replace(" ", "_") in marker_terms or symbol and symbol in marker_terms:
            rows.append(
                {
                    "id": f"heatmap:{row.get('symbol')}",
                    "label": row.get("label") or row.get("symbol"),
                    "type": "heatmap_tile",
                    "provider": row.get("provider"),
                    "source_status": row.get("source_status"),
                    "confidence": row.get("confidence"),
                    "fetched_at": row.get("fetched_at"),
                    "caveat": row.get("caveat"),
                    "data_gap": row.get("data_gap"),
                    "not_financial_advice": True,
                }
            )
    return rows[:limit]


def _heatmap_context(marker: dict[str, Any] | None, heatmap_rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    if not heatmap_rows:
        return []
    marker_text = " ".join(
        [
            str((marker or {}).get("title") or ""),
            str((marker or {}).get("summary") or ""),
            str((marker or {}).get("region") or ""),
            " ".join(str(item) for item in _list((marker or {}).get("related_asset_node_ids"))),
        ]
    ).lower()
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in heatmap_rows:
        change = abs(_as_float(row.get("daily_return_pct")))
        sector = _norm(row.get("sector"))
        industry = _norm(row.get("industry"))
        relevance = change
        if sector and sector.replace(" ", "_") in marker_text:
            relevance += 8
        if industry and industry.replace(" ", "_") in marker_text:
            relevance += 4
        scored.append((relevance, row))
    output = []
    for _, row in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]:
        output.append(
            {
                "symbol": row.get("symbol"),
                "label": row.get("label"),
                "sector": row.get("sector"),
                "industry": row.get("industry"),
                "market_cap_weight": row.get("market_cap_weight"),
                "daily_return_pct": row.get("daily_return_pct"),
                "color_bucket": row.get("color_bucket"),
                "provider": row.get("provider"),
                "source_status": row.get("source_status"),
                "freshness": row.get("freshness"),
                "fetched_at": row.get("fetched_at"),
                "confidence": row.get("confidence"),
                "caveat": row.get("caveat"),
                "data_gap": row.get("data_gap"),
                "not_financial_advice": True,
            }
        )
    return output


def build_map_news_event_fusion_contract(
    *,
    war_room_map: dict[str, Any] | None = None,
    news_dashboard: dict[str, Any] | None = None,
    event_graph: dict[str, Any] | None = None,
    provider_health: dict[str, Any] | list[dict[str, Any]] | None = None,
    layer_runtime: dict[str, Any] | None = None,
    market_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    war_data = _data(war_room_map)
    news_data = _data(news_dashboard)
    graph_data = _data(event_graph)
    layer_data = _data(layer_runtime)
    market_data = _data(market_intelligence)
    provider_rows = _records(_data(provider_health).get("data") if isinstance(provider_health, dict) else provider_health)
    if not provider_rows and isinstance(provider_health, dict):
        provider_rows = _records(provider_health.get("data")) or _records(provider_health)

    markers = _records(war_data.get("markers"))
    layers = _records(war_data.get("layers")) or _records(layer_data.get("layers"))
    news_rows = _combined_news_rows(news_data)
    nodes = _records(graph_data.get("nodes"))
    edges = _records(graph_data.get("edges"))
    heatmap_rows = _records(market_data.get("market_heatmap"))
    live_statuses = {"live/fresh", "cached", "stale"}
    unavailable_sources = _dedupe_unavailable_sources([
        {
            "provider": row.get("provider"),
            "source": row.get("source"),
            "layer_id": row.get("layer_id"),
            "status": row.get("status") or row.get("source_status") or row.get("availability"),
            "availability": row.get("availability"),
            "recommended_action": row.get("recommended_action"),
            "caveat": row.get("caveat") or row.get("warning") or "",
            "data_gap": row.get("data_gap") or row.get("error") or "",
        }
        for row in [*provider_rows, *layers]
        if row.get("availability") == "unavailable"
        or str(row.get("status") or row.get("source_status") or "").lower()
        in {"missing-key", "unavailable", "provider-required", "forbidden/subscription-blocked"}
    ])
    layer_health = [
        {
            "layer_id": row.get("layer_id"),
            "label": row.get("label"),
            "domain": row.get("domain"),
            "provider": row.get("provider"),
            "availability": row.get("availability"),
            "row_count": row.get("row_count"),
            "source_status": row.get("source_status"),
            "latest_fetched_at": row.get("latest_fetched_at"),
            "recommended_action": row.get("recommended_action"),
            "caveat": row.get("caveat"),
        }
        for row in layers
    ]
    provider_health_rows = [
        {
            "provider": row.get("provider"),
            "status": row.get("status") or row.get("source_status"),
            "availability": row.get("availability"),
            "row_count": row.get("row_count"),
            "fetched_at": row.get("fetched_at"),
            "recommended_action": row.get("recommended_action"),
            "caveat": row.get("caveat") or row.get("warning") or "",
            "data_gap": row.get("data_gap") or row.get("error") or "",
        }
        for row in provider_rows
    ]
    timeline_windows = _records(war_data.get("timeline_filters")) + _records(war_data.get("compare_windows"))
    event_contexts = [
        _event_context(marker=marker, news_rows=news_rows, nodes=nodes, edges=edges, heatmap_rows=heatmap_rows)
        for marker in markers
    ]
    selected_context = max(
        event_contexts,
        key=lambda row: (_as_float(row.get("context_score")), str(row.get("marker_id") or "")),
        default={},
    )
    selected_id = selected_context.get("marker_id")
    selected = next((marker for marker in markers if marker.get("marker_id") == selected_id), None) or _select_marker(markers)
    selected_id = selected.get("marker_id") if selected else None
    if selected_id and selected_context.get("marker_id") != selected_id:
        selected_context = next((row for row in event_contexts if row.get("marker_id") == selected_id), {})
    related_news = _records(selected_context.get("related_news"))
    event_links = _records(selected_context.get("event_links"))
    connected_assets = _records(selected_context.get("connected_assets"))
    heatmap_context = _records(selected_context.get("heatmap_context"))
    source_register = []
    for collection, fallback_provider, fallback_source in [
        (markers, "war_room_map", "markers"),
        (related_news, "news_dashboard", "related_news"),
        (event_links, "event_asset_graph", "event_links"),
        (heatmap_context, "market_intelligence", "market_heatmap"),
        (layer_health, "layer_runtime", "layers"),
        (provider_health_rows, "provider_health", "provider_health"),
    ]:
        source_register.extend(_source_row(row, fallback_provider=fallback_provider, fallback_source=fallback_source) for row in collection)

    live_like = sum(1 for row in source_register if row.get("source_status") in live_statuses)
    fixture_like = sum(1 for row in source_register if "fixture" in str(row.get("source_status") or ""))
    proxy_like = sum(1 for row in source_register if "proxy" in str(row.get("source_status") or ""))
    readiness = {
        "fusion_ready": bool(markers and (related_news or event_links or heatmap_context)),
        "live_claim_allowed": live_like > 0,
        "live_source_count": live_like,
        "fixture_source_count": fixture_like,
        "proxy_source_count": proxy_like,
        "unavailable_source_count": len(unavailable_sources),
        "map_news_event_contract_only": True,
        "broker_execution_added": False,
        "auth_added": False,
        "billing_added": False,
        "hosted_persistence_added": False,
        "external_source_copied": False,
    }
    return {
        "map_news_event_fusion_version": MAP_NEWS_EVENT_FUSION_VERSION,
        "workspace": "map-news-event-fusion",
        "selected_marker_id": selected_id,
        "selected_marker": selected or {},
        "markers": markers,
        "news_rows": news_rows,
        "event_contexts": event_contexts,
        "related_news": related_news,
        "event_links": event_links,
        "connected_assets": connected_assets,
        "heatmap_context": heatmap_context,
        "layer_health": layer_health,
        "provider_health": provider_health_rows,
        "timeline_windows": timeline_windows,
        "unavailable_sources": unavailable_sources,
        "source_register": source_register,
        "readiness": readiness,
        "evidence_refs": [
            {
                "source": "map-news-monitoring behavior reference",
                "license_stance": "behavior-only",
                "adopted_behavior": "Map-linked news/source/provider context, clean-room only.",
            },
            {
                "source": "earth-observation map behavior reference",
                "license_stance": "behavior-only",
                "adopted_behavior": "Timeline and compare readiness concepts, clean-room only.",
            },
            {
                "source": "TradingView heatmap benchmark",
                "license_stance": "public-product-behavior-reference",
                "adopted_behavior": "Heatmap outlier context by size/color, clean-room only.",
            },
            {
                "source": "agent workflow behavior reference",
                "license_stance": "direct-use-allowed",
                "adopted_behavior": "Contract-first, source-driven, test-driven workflow.",
            },
        ],
        "summary": {
            "workspace": "map-news-event-fusion",
            "marker_count": len(markers),
            "event_context_count": len(event_contexts),
            "context_linked_marker_count": sum(1 for row in event_contexts if row.get("context_status") != "event-only"),
            "related_news_count": len(related_news),
            "event_link_count": len(event_links),
            "connected_asset_count": len(connected_assets),
            "heatmap_context_count": len(heatmap_context),
            "layer_count": len(layer_health),
            "provider_count": len(provider_health_rows),
            "unavailable_source_count": len(unavailable_sources),
            "selected_marker_id": selected_id,
            "source_status": "live/fresh" if live_like else "fixture/proxy",
            "non_advisory": True,
            "generated_at": _now_iso(),
        },
        "caveat": "Map-news-event fusion links existing source-labeled contracts; it does not create live provider coverage or trading advice.",
    }
