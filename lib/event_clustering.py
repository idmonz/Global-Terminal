from __future__ import annotations

from collections import Counter
from typing import Any

from .news_intelligence import classify_news_asset_tags, classify_news_region, normalize_news_item

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "after",
    "over",
    "into",
    "amid",
    "says",
    "new",
    "news",
    "market",
    "markets",
}


def _records(items: Any) -> list[dict[str, Any]]:
    if items is None:
        return []
    if hasattr(items, "to_dict"):
        return items.to_dict(orient="records")
    if isinstance(items, list):
        return [dict(item) for item in items if isinstance(item, dict)]
    if isinstance(items, dict):
        return [items]
    return []


def _frame(rows: list[dict[str, Any]]):
    return pd.DataFrame(rows) if pd is not None else rows


def _tokens(text: str) -> list[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return [token for token in cleaned.split() if len(token) > 3 and token not in STOPWORDS]


def _cluster(rows: list[dict[str, Any]], key_name: str, key_getter) -> Any:
    clusters: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        keys = key_getter(row)
        if isinstance(keys, str):
            keys = [keys]
        for key in keys or ["Unclassified"]:
            clusters.setdefault(str(key), []).append(row)
    output = []
    for key, group in clusters.items():
        severities = [str(row.get("severity", "watch")).lower() for row in group]
        output.append(
            {
                key_name: key,
                "headline_count": len(group),
                "high_count": sum(severity in {"critical", "high"} for severity in severities),
                "severity": "high" if any(severity in {"critical", "high"} for severity in severities) else "medium" if "medium" in severities else "watch",
                "latest_title": group[0].get("title"),
                "method": "deterministic event clustering",
            }
        )
    return _frame(sorted(output, key=lambda item: (item["high_count"], item["headline_count"]), reverse=True))


def _normalized(items: Any) -> list[dict[str, Any]]:
    return [normalize_news_item(row) for row in _records(items)]


def cluster_news_by_keyword(items: Any, top_n: int = 12):
    rows = _normalized(items)
    keyword_counts = Counter()
    row_keywords: list[tuple[dict[str, Any], list[str]]] = []
    for row in rows:
        tokens = _tokens(f"{row.get('title', '')} {row.get('summary', '')}")
        keyword_counts.update(tokens)
        row_keywords.append((row, tokens))
    top = {keyword for keyword, _ in keyword_counts.most_common(top_n)}
    cluster_rows = []
    for keyword in top:
        group = [row for row, tokens in row_keywords if keyword in tokens]
        if not group:
            continue
        severities = [str(row.get("severity", "watch")).lower() for row in group]
        cluster_rows.append(
            {
                "keyword": keyword,
                "headline_count": len(group),
                "high_count": sum(severity in {"critical", "high"} for severity in severities),
                "severity": "high" if any(severity in {"critical", "high"} for severity in severities) else "medium" if "medium" in severities else "watch",
                "latest_title": group[0].get("title"),
                "method": "deterministic keyword clustering",
            }
        )
    return _frame(cluster_rows)


def cluster_news_by_region(items: Any):
    rows = _normalized(items)
    return _cluster(rows, "region", lambda row: row.get("region") or classify_news_region(row))


def cluster_news_by_asset(items: Any):
    rows = _normalized(items)
    return _cluster(rows, "asset_tag", lambda row: row.get("asset_tags") or classify_news_asset_tags(row))


def build_event_cluster_cards(items: Any, limit: int = 8):
    keyword = cluster_news_by_keyword(items)
    region = cluster_news_by_region(items)
    asset = cluster_news_by_asset(items)
    rows = []
    for source_name, frame in [("keyword", keyword), ("region", region), ("asset", asset)]:
        if hasattr(frame, "empty"):
            records = frame.head(limit).to_dict(orient="records") if not frame.empty else []
        else:
            records = frame[:limit] if isinstance(frame, list) else []
        for record in records:
            label = record.get(source_name) or record.get("asset_tag") or record.get("region") or record.get("keyword")
            rows.append(
                {
                    "title": f"{source_name.title()} Cluster: {label}",
                    "summary": f"{record.get('headline_count', 0)} headline(s), {record.get('high_count', 0)} high-severity item(s).",
                    "severity": record.get("severity", "watch"),
                    "tags": [source_name, str(label)],
                    "method": record.get("method", "deterministic event clustering"),
                }
            )
    return rows[:limit]
