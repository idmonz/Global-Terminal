from __future__ import annotations

from typing import Any

from .market_impact_engine import build_event_to_scenario_evidence, build_news_market_impact_table
from .news_asset_linker import build_related_asset_list, classify_event_domain, classify_market_channel

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


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


def _frame(rows: list[dict[str, Any]]):
    return pd.DataFrame(rows) if pd is not None else rows


def _node_id(node_type: str, label: Any) -> str:
    safe = str(label or "unknown").strip() or "unknown"
    return f"{node_type}:{safe}"


def build_catalyst_nodes(events: Any = None, impact_rows: Any = None):
    nodes: dict[str, dict[str, Any]] = {}
    for event in _records(events):
        event_id = event.get("event_id") or event.get("title")
        nodes[_node_id("news_event", event_id)] = {
            "node_id": _node_id("news_event", event_id),
            "label": event.get("title") or event_id,
            "node_type": "news_event",
            "domain": event.get("domain") or classify_event_domain(event),
            "score": event.get("severity_score") or 30,
        }
        for key, node_type in [("region", "region"), ("country", "country")]:
            if event.get(key):
                nodes[_node_id(node_type, event.get(key))] = {"node_id": _node_id(node_type, event.get(key)), "label": event.get(key), "node_type": node_type, "domain": "geography", "score": 40}
        for channel in classify_market_channel(event):
            nodes[_node_id("macro_factor", channel)] = {"node_id": _node_id("macro_factor", channel), "label": channel, "node_type": "macro_factor", "domain": channel, "score": 45}
        for asset in build_related_asset_list(event):
            ticker = asset["related_tickers"][0]
            node_type = "crypto_factor" if asset.get("asset_class") == "crypto" else "commodity" if asset.get("asset_class") in {"commodity", "commodity_etf"} else "asset"
            nodes[_node_id(node_type, ticker)] = {"node_id": _node_id(node_type, ticker), "label": ticker, "node_type": node_type, "domain": asset.get("asset_class"), "score": asset.get("relevance_score")}
    for row in _records(impact_rows):
        if row.get("ticker"):
            nodes.setdefault(
                _node_id("asset", row.get("ticker")),
                {"node_id": _node_id("asset", row.get("ticker")), "label": row.get("ticker"), "node_type": "asset", "domain": row.get("asset_class"), "score": row.get("relevance_score") or 30},
            )
        if row.get("market_channel"):
            for channel in str(row.get("market_channel")).split(","):
                channel = channel.strip()
                if channel:
                    nodes.setdefault(_node_id("macro_factor", channel), {"node_id": _node_id("macro_factor", channel), "label": channel, "node_type": "macro_factor", "domain": channel, "score": 45})
    nodes[_node_id("scenario", "news impact evidence")] = {
        "node_id": _node_id("scenario", "news impact evidence"),
        "label": "news impact evidence",
        "node_type": "scenario",
        "domain": "scenario",
        "score": 50,
    }
    return _frame(list(nodes.values()))


def build_catalyst_edges(events: Any = None, impact_rows: Any = None, scenario_rows: Any = None):
    edges = []
    for event in _records(events):
        event_key = _node_id("news_event", event.get("event_id") or event.get("title"))
        if event.get("region"):
            edges.append({"source": event_key, "target": _node_id("region", event.get("region")), "edge_type": "region_link", "weight": 45, "caveat": "Event region is source/heuristic metadata."})
        if event.get("country"):
            edges.append({"source": event_key, "target": _node_id("country", event.get("country")), "edge_type": "mentions", "weight": 45, "caveat": "Country mention from event metadata."})
        for channel in classify_market_channel(event):
            edges.append({"source": event_key, "target": _node_id("macro_factor", channel), "edge_type": "macro_channel", "weight": 45, "caveat": "Potential market channel; not causality."})
        for asset in build_related_asset_list(event):
            ticker = asset["related_tickers"][0]
            node_type = "crypto_factor" if asset.get("asset_class") == "crypto" else "commodity" if asset.get("asset_class") in {"commodity", "commodity_etf"} else "asset"
            edges.append({"source": event_key, "target": _node_id(node_type, ticker), "edge_type": "asset_exposure", "weight": asset.get("relevance_score"), "caveat": asset.get("caveat")})
    for row in _records(impact_rows):
        event_key = _node_id("news_event", row.get("event_id"))
        ticker = row.get("ticker")
        if ticker:
            edges.append({"source": event_key, "target": _node_id("asset", ticker), "edge_type": "observed_move", "weight": abs(float(row.get("return_1d_pct") or 0)) * 10, "caveat": row.get("causality_caveat")})
    for row in _records(scenario_rows):
        event_key = _node_id("news_event", row.get("event_id"))
        edges.append({"source": event_key, "target": _node_id("scenario", "news impact evidence"), "edge_type": "scenario_evidence", "weight": row.get("news_impact_evidence") or 0, "caveat": row.get("confidence_caveat")})
    return _frame(edges)


def build_catalyst_graph(events: Any = None, impact_rows: Any = None) -> dict[str, Any]:
    if impact_rows is None:
        impact_rows, _ = build_news_market_impact_table(events)
    scenario_rows = build_event_to_scenario_evidence(events, impact_rows)
    nodes = build_catalyst_nodes(events, impact_rows)
    edges = build_catalyst_edges(events, impact_rows, scenario_rows)
    return {
        "nodes": nodes,
        "edges": edges,
        "scenario_evidence": scenario_rows,
        "caveat": "Catalyst graph shows mentions, exposure mappings, observed proxy moves, and scenario evidence without causal claims.",
    }


def build_catalyst_cluster_summary(events: Any = None, graph: dict[str, Any] | None = None):
    graph = graph or build_catalyst_graph(events)
    edges = graph.get("edges")
    rows = _records(edges)
    summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        edge_type = row.get("edge_type") or "unknown"
        item = summary.setdefault(edge_type, {"cluster": edge_type, "edge_count": 0, "total_weight": 0.0, "caveat": "Graph edge cluster summary."})
        item["edge_count"] += 1
        item["total_weight"] += float(row.get("weight") or 0)
    for item in summary.values():
        item["average_weight"] = round(item["total_weight"] / max(1, item["edge_count"]), 1)
    return _frame(sorted(summary.values(), key=lambda row: row["edge_count"], reverse=True))
