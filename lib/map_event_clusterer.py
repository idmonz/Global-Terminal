from __future__ import annotations

from collections import defaultdict
from typing import Any


SEVERITY_SCORE = {"low": 20, "watch": 35, "medium": 55, "elevated": 65, "high": 80, "critical": 95}


def cluster_events_by_region(events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events or []:
        grouped[str(event.get("region") or "Global")].append(event)
    return [{"cluster_id": region.lower().replace(" ", "_"), "region": region, "events": rows, "count": len(rows), "severity_score": compute_cluster_severity(rows)} for region, rows in grouped.items()]


def cluster_events_by_proximity(events: list[dict[str, Any]] | None = None, *, precision: int = 1) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events or []:
        if event.get("lat") is None or event.get("lon") is None:
            key = str(event.get("region") or "unknown")
        else:
            key = f"{round(float(event['lat']), precision)}:{round(float(event['lon']), precision)}"
        grouped[key].append(event)
    return [{"cluster_id": key, "events": rows, "count": len(rows), "severity_score": compute_cluster_severity(rows)} for key, rows in grouped.items()]


def compute_cluster_severity(events: list[dict[str, Any]] | None = None) -> float:
    if not events:
        return 0.0
    scores = [SEVERITY_SCORE.get(str(event.get("severity") or "watch").lower(), 35) for event in events]
    return round(min(100.0, max(scores) + max(0, len(scores) - 1) * 3), 2)


def build_cluster_tooltip(cluster: dict[str, Any]) -> str:
    titles = [str(event.get("title") or "event") for event in cluster.get("events", [])[:5]]
    return f"Cluster {cluster.get('cluster_id')}: {cluster.get('count', 0)} events; severity {cluster.get('severity_score')}; " + "; ".join(titles)


def build_cluster_summary_cards(clusters: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    cards = []
    for cluster in sorted(clusters or [], key=lambda item: item.get("severity_score", 0), reverse=True):
        cards.append({"title": str(cluster.get("region") or cluster.get("cluster_id")), "summary": build_cluster_tooltip(cluster), "severity": "high" if cluster.get("severity_score", 0) >= 75 else "medium" if cluster.get("severity_score", 0) >= 50 else "watch", "tags": ["cluster", str(cluster.get("count", 0))], "freshness": "estimated"})
    return cards
