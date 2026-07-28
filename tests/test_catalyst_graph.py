from __future__ import annotations

from lib.catalyst_graph import build_catalyst_cluster_summary, build_catalyst_edges, build_catalyst_graph, build_catalyst_nodes


def test_catalyst_graph_schema():
    events = [{"event_id": "e1", "title": "Taiwan semiconductor tension", "region": "Asia", "country": "Taiwan", "severity": "high"}]
    graph = build_catalyst_graph(events)
    assert {"nodes", "edges", "scenario_evidence", "caveat"}.issubset(graph)
    assert {"node_id", "node_type", "label"}.issubset(graph["nodes"].columns)
    assert {"source", "target", "edge_type", "weight"}.issubset(graph["edges"].columns)
    summary = build_catalyst_cluster_summary(events, graph)
    assert not summary.empty


def test_catalyst_node_and_edge_builders():
    events = [{"event_id": "e1", "title": "Iran Hormuz tanker sanctions", "region": "Middle East", "severity": "critical"}]
    nodes = build_catalyst_nodes(events)
    edges = build_catalyst_edges(events)
    assert not nodes.empty
    assert not edges.empty
