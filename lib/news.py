from __future__ import annotations

import pandas as pd

from .data_status import error_result, ok_result


def dedupe_news_items(items: pd.DataFrame) -> pd.DataFrame:
    if items is None or items.empty:
        return pd.DataFrame()
    frame = items.copy()
    for column in ["title", "url"]:
        if column not in frame.columns:
            frame[column] = ""
    return frame.drop_duplicates(subset=["title", "url"])


def classify_asset_news(title: str) -> str:
    text = title.lower()
    if any(word in text for word in ["oil", "crude", "opec", "refinery"]):
        return "oil"
    if any(word in text for word in ["bitcoin", "ethereum", "crypto"]):
        return "crypto"
    if any(word in text for word in ["fed", "rates", "inflation"]):
        return "macro"
    if any(word in text for word in ["shipping", "tanker", "suez", "hormuz"]):
        return "shipping"
    return "equities"


def build_news_dashboard(items: pd.DataFrame | None = None) -> tuple[pd.DataFrame, object]:
    frame = dedupe_news_items(items if items is not None else pd.DataFrame())
    if frame.empty:
        return frame, error_result(source="news", provider="news", error="No news items supplied.")
    frame["classification"] = frame["title"].astype(str).apply(classify_asset_news)
    return frame, ok_result(frame, source="provided news", provider="news", coverage=f"{len(frame)} items")

