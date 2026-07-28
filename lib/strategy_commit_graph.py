from __future__ import annotations
from typing import Any


def build_strategy_commit_graph(commits: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = [{"id": c.get("commit_id"), "strategy_id": c.get("strategy_id"), "status": c.get("status"), "created_at": c.get("created_at")} for c in commits or []]
    edges = [{"source": c.get("parent_commit_id"), "target": c.get("commit_id")} for c in commits or [] if c.get("parent_commit_id")]
    roots = [n for n in nodes if not any(e["target"] == n["id"] for e in edges)]
    return {"nodes": nodes, "edges": edges, "root_count": len(roots), "commit_count": len(nodes)}
