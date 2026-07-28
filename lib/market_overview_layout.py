from __future__ import annotations

from typing import Any

from .click_path_engine import build_page_next_actions
from .heatmap_layout_engine import build_heatmap_layout
from .summary_keyword_engine import build_actionable_summary_phrases, extract_summary_keywords


def build_overview_summary(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    risk_state = str(context.get("risk_state") or "watch")
    gaps = list(context.get("provider_gaps") or context.get("data_gaps") or [])
    return {
        "title": "Executive Market Summary",
        "key_changes": list(context.get("key_changes") or build_actionable_summary_phrases(context, limit=5)),
        "risk_state": risk_state,
        "data_confidence": context.get("data_confidence", "source-labeled"),
        "source_freshness": context.get("source_freshness", "unknown"),
        "provider_gaps": gaps,
    }


def build_market_board_sections(
    *,
    cross_asset_rows: Any = None,
    equity_rows: Any = None,
    crypto_rows: Any = None,
    provider_rows: Any = None,
) -> dict[str, Any]:
    return {
        "cross_asset_heatmap": build_heatmap_layout(cross_asset_rows or [], title="Cross-Asset Heatmap", size_mode="equal", color_mode="daily_change", group_mode="asset_class"),
        "equity_heatmap": build_heatmap_layout(equity_rows or [], title="Equity Heatmap", size_mode="market_cap", color_mode="daily_change", group_mode="sector"),
        "crypto_heatmap": build_heatmap_layout(crypto_rows or [], title="Crypto Heatmap", size_mode="tvl", color_mode="daily_change", group_mode="crypto_sector"),
        "provider_health_heatmap": build_heatmap_layout(provider_rows or [], title="Provider Health", size_mode="equal", color_mode="provider_health", group_mode="provider_domain"),
    }


def build_market_overview_payload(
    *,
    context: dict[str, Any] | None = None,
    cross_asset_rows: Any = None,
    equity_rows: Any = None,
    crypto_rows: Any = None,
    provider_rows: Any = None,
    news_events: Any = None,
    rmi: dict[str, Any] | None = None,
    volatility: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}
    summary = build_overview_summary(context)
    boards = build_market_board_sections(cross_asset_rows=cross_asset_rows, equity_rows=equity_rows, crypto_rows=crypto_rows, provider_rows=provider_rows)
    return {
        "summary": summary,
        "keywords": extract_summary_keywords({"summary": summary, "events": news_events}),
        "market_board": boards,
        "quotes_movers_panel": context.get("movers", []),
        "event_timeline": news_events or [],
        "rmi": rmi or {},
        "volatility": volatility or {},
        "click_next": build_page_next_actions("Overview", context),
        "methodology": "Internal project-native rows; optional widgets are visual supplements only.",
    }
