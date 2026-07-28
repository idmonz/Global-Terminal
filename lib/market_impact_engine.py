from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
from typing import Any

from .data_status import combine_results, error_result, ok_result
from .news_asset_linker import build_related_asset_list, classify_market_channel

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


def _close_series(price_data: Any):
    if pd is None or price_data is None or getattr(price_data, "empty", True):
        return None
    frame = price_data.copy()
    if isinstance(getattr(frame, "columns", None), pd.MultiIndex):
        frame.columns = [" ".join(str(part) for part in col if str(part)).strip() for col in frame.columns]
    close_col = next((col for col in ["Adj Close", "Close", "adj close", "close"] if col in frame.columns), None)
    if close_col is None:
        close_col = next((col for col in frame.columns if str(col).lower().endswith("close")), None)
    if close_col is None:
        return None
    series = pd.to_numeric(frame[close_col], errors="coerce").dropna()
    return series if not series.empty else None


def _volume_series(price_data: Any):
    if pd is None or price_data is None or getattr(price_data, "empty", True):
        return None
    frame = price_data.copy()
    if isinstance(getattr(frame, "columns", None), pd.MultiIndex):
        frame.columns = [" ".join(str(part) for part in col if str(part)).strip() for col in frame.columns]
    col = next((col for col in ["Volume", "volume"] if col in frame.columns), None)
    if col is None:
        return None
    series = pd.to_numeric(frame[col], errors="coerce").dropna()
    return series if not series.empty else None


def _pct_change(series, periods: int):
    if series is None or len(series) <= periods:
        return None
    try:
        return float((series.iloc[-1] / series.iloc[-1 - periods] - 1) * 100)
    except Exception:
        return None


def compute_pre_post_market_move(price_data: Any, event_timestamp: Any, window: int = 3) -> dict[str, Any]:
    if pd is None:
        return {"pre_post_return_pct": None, "data_gap": "pandas unavailable", "label": "Data gap"}
    close = _close_series(price_data)
    if close is None:
        return {"pre_post_return_pct": None, "data_gap": "No close price series available.", "label": "Data gap"}
    event_time = pd.to_datetime(event_timestamp, utc=True, errors="coerce")
    if pd.isna(event_time):
        return {"pre_post_return_pct": None, "data_gap": "Event timestamp unavailable.", "label": "Data gap"}
    indexed = close.copy()
    indexed.index = pd.to_datetime(indexed.index, utc=True, errors="coerce")
    before = indexed[indexed.index <= event_time].tail(window)
    after = indexed[indexed.index >= event_time].head(window)
    if before.empty or after.empty:
        return {"pre_post_return_pct": None, "data_gap": "Insufficient pre/post price observations.", "label": "Data gap"}
    value = float((after.iloc[-1] / before.iloc[0] - 1) * 100)
    return {"pre_post_return_pct": round(value, 3), "data_gap": None, "label": "Observed related market move"}


def compute_recent_asset_reaction(
    ticker: str,
    price_data: Any = None,
    *,
    fetch_market_data: bool = False,
) -> tuple[dict[str, Any], Any]:
    status = None
    if price_data is None and fetch_market_data:
        try:
            from .market_data import fetch_history

            price_data, status = fetch_history(ticker, period="3mo")
        except Exception as exc:
            status = error_result(source=f"{ticker} price history", provider="market_data", error=str(exc), coverage="missing")
    close = _close_series(price_data)
    volume = _volume_series(price_data)
    if close is None:
        payload = {
            "ticker": ticker,
            "latest_return_pct": None,
            "return_1d_pct": None,
            "return_1w_pct": None,
            "return_1m_pct": None,
            "realized_volatility_change": None,
            "volume_zscore": None,
            "reaction_label": "Data gap",
            "data_gap": "Price history unavailable; no market reaction is inferred.",
        }
        warning = payload["data_gap"]
        if status is not None and getattr(status, "error", None):
            warning = f"{warning} Provider detail: {status.error}"
        return payload, ok_result(
            payload,
            source=f"{ticker} price reaction",
            provider="market_impact_engine",
            warning=warning,
            is_estimated=True,
            coverage="price history missing; relation mapping only",
        )
    returns = close.pct_change().dropna()
    recent_vol = float(returns.tail(5).std() * sqrt(252) * 100) if len(returns) >= 5 else None
    prior_vol = float(returns.tail(25).head(20).std() * sqrt(252) * 100) if len(returns) >= 25 else None
    volume_z = None
    if volume is not None and len(volume) >= 20:
        vol_mean = float(volume.tail(20).mean())
        vol_std = float(volume.tail(20).std() or 0)
        volume_z = None if vol_std == 0 else round(float((volume.iloc[-1] - vol_mean) / vol_std), 3)
    payload = {
        "ticker": ticker,
        "latest_return_pct": _pct_change(close, 1),
        "return_1d_pct": _pct_change(close, 1),
        "return_1w_pct": _pct_change(close, 5),
        "return_1m_pct": _pct_change(close, 21),
        "realized_volatility_change": None if recent_vol is None or prior_vol is None else round(recent_vol - prior_vol, 3),
        "volume_zscore": volume_z,
        "reaction_label": "Proxy reaction",
        "data_gap": None,
    }
    return payload, status or ok_result(payload, source=f"{ticker} price reaction", provider="market_impact_engine", coverage="computed from supplied price data")


def compute_volatility_reaction(price_data: Any = None) -> dict[str, Any]:
    close = _close_series(price_data)
    if pd is None or close is None:
        return {"volatility_change": None, "data_gap": "Price history unavailable.", "label": "Data gap"}
    returns = close.pct_change().dropna()
    if len(returns) < 25:
        return {"volatility_change": None, "data_gap": "Insufficient observations for volatility comparison.", "label": "Data gap"}
    recent = float(returns.tail(5).std() * sqrt(252) * 100)
    prior = float(returns.tail(25).head(20).std() * sqrt(252) * 100)
    return {"volatility_change": round(recent - prior, 3), "data_gap": None, "label": "Correlation context"}


def build_market_impact_context(news_or_events: Any = None, *, price_data: dict[str, Any] | None = None, fetch_market_data: bool = False) -> dict[str, Any]:
    events = _records(news_or_events)
    impact_table, status = build_news_market_impact_table(events, price_data=price_data, fetch_market_data=fetch_market_data)
    return {
        "events": events,
        "impact_table": impact_table,
        "status": status,
        "channels": sorted({channel for event in events for channel in classify_market_channel(event)}),
        "caveat": "Market impact context is related-asset and proxy/correlation analysis, not causal attribution.",
    }


def compute_cross_asset_impact_matrix(
    events: Any = None,
    *,
    price_data: dict[str, Any] | None = None,
    fetch_market_data: bool = False,
):
    rows = []
    statuses = []
    for event in _records(events):
        related = build_related_asset_list(event)
        if not related:
            related = [{"related_tickers": [], "asset_class": "unknown", "relevance_score": 0, "reason": "No related asset mapping.", "caveat": "No mapping."}]
        for asset in related[:10]:
            ticker = asset["related_tickers"][0] if asset.get("related_tickers") else None
            reaction, reaction_status = compute_recent_asset_reaction(
                ticker or "unmapped",
                None if ticker is None else (price_data or {}).get(ticker),
                fetch_market_data=bool(ticker and fetch_market_data),
            )
            statuses.append(reaction_status)
            rows.append(
                {
                    "event_id": event.get("event_id") or event.get("title"),
                    "event_title": event.get("title"),
                    "domain": event.get("domain") or "unknown",
                    "market_channel": ", ".join(classify_market_channel(event)),
                    "ticker": ticker,
                    "asset_class": asset.get("asset_class"),
                    "relevance_score": asset.get("relevance_score"),
                    "potential_channel": asset.get("reason"),
                    "latest_return_pct": reaction.get("latest_return_pct"),
                    "return_1d_pct": reaction.get("return_1d_pct"),
                    "return_1w_pct": reaction.get("return_1w_pct"),
                    "return_1m_pct": reaction.get("return_1m_pct"),
                    "realized_volatility_change": reaction.get("realized_volatility_change"),
                    "volume_zscore": reaction.get("volume_zscore"),
                    "impact_label": reaction.get("reaction_label") if not reaction.get("data_gap") else "Data gap",
                    "evidence_language": "Observed related market move" if not reaction.get("data_gap") else "Data gap",
                    "causality_caveat": "Correlation/proxy context only; no causal claim.",
                    "data_gap": reaction.get("data_gap"),
                }
            )
    frame = _frame(rows)
    if statuses:
        status = combine_results([item for item in statuses if item is not None], provider="market_impact_engine", source="cross asset impact matrix")
        missing_count = sum(1 for row in rows if row.get("data_gap"))
        if missing_count and getattr(status, "ok", False):
            status.warning = f"{missing_count} related asset rows lack price history; impact matrix shows relevance and data-gap context only."
            status.is_estimated = True
            status.freshness_status = "estimated"
    else:
        status = error_result(source="cross asset impact matrix", provider="market_impact_engine", error="No events or related assets supplied.", coverage="missing")
    return frame, status


def compute_event_market_sensitivity(event: dict[str, Any], impact_rows: Any = None) -> dict[str, Any]:
    rows = [row for row in _records(impact_rows) if str(row.get("event_id")) == str(event.get("event_id") or event.get("title"))]
    if not rows:
        return {
            "event_id": event.get("event_id") or event.get("title"),
            "sensitivity_score": 0,
            "evidence_weight": 0,
            "caveat": "No related market reaction rows available.",
        }
    relevance = sum(float(row.get("relevance_score") or 0) for row in rows) / max(1, len(rows))
    move_component = sum(abs(float(row.get("return_1d_pct") or 0)) for row in rows)
    vol_component = sum(abs(float(row.get("realized_volatility_change") or 0)) for row in rows)
    score = min(100, relevance * 0.45 + move_component * 8 + vol_component * 1.5)
    return {
        "event_id": event.get("event_id") or event.get("title"),
        "sensitivity_score": round(score, 1),
        "evidence_weight": round(min(100, score * 0.8), 1),
        "caveat": "Sensitivity is proxy/correlation evidence for scenario context.",
    }


def build_news_market_impact_table(
    news_or_events: Any = None,
    *,
    price_data: dict[str, Any] | None = None,
    fetch_market_data: bool = False,
):
    frame, status = compute_cross_asset_impact_matrix(news_or_events, price_data=price_data, fetch_market_data=fetch_market_data)
    return frame, status


def build_market_impact_cards(news_or_events: Any = None, impact_rows: Any = None, limit: int = 8) -> list[dict[str, Any]]:
    rows = _records(impact_rows)
    if not rows:
        frame, _ = build_news_market_impact_table(news_or_events)
        rows = _records(frame)
    cards = []
    for row in rows[:limit]:
        cards.append(
            {
                "title": f"{row.get('ticker') or 'Unmapped'} impact context",
                "summary": f"{row.get('event_title') or 'Event'} -> {row.get('potential_channel') or 'potential channel'}",
                "severity": "watch" if row.get("data_gap") else "elevated",
                "freshness": "estimated" if row.get("data_gap") else "fresh",
                "source": "market_impact_engine",
                "tags": [row.get("market_channel"), row.get("impact_label"), row.get("asset_class")],
                "bullets": [row.get("evidence_language"), row.get("causality_caveat"), row.get("data_gap") or "Observed fields are related market context."],
            }
        )
    return cards


def build_event_to_scenario_evidence(news_or_events: Any = None, impact_rows: Any = None):
    events = _records(news_or_events)
    impact = impact_rows
    if impact is None:
        impact, _ = build_news_market_impact_table(events)
    rows = []
    for event in events:
        sensitivity = compute_event_market_sensitivity(event, impact)
        related_assets = sorted({row.get("ticker") for row in _records(impact) if str(row.get("event_id")) == str(event.get("event_id") or event.get("title")) and row.get("ticker")})
        rows.append(
            {
                "event_id": event.get("event_id") or event.get("title"),
                "event_title": event.get("title"),
                "news_impact_evidence": sensitivity["evidence_weight"],
                "related_assets": related_assets,
                "catalyst_clusters": classify_market_channel(event),
                "data_gaps": "; ".join(sorted({row.get("data_gap") for row in _records(impact) if row.get("data_gap")})) or None,
                "confidence_caveat": "News impact evidence is neutral proxy/correlation context.",
            }
        )
    return _frame(rows)


def build_energy_market_impact_context(energy_payload: dict[str, Any] | None = None, macro_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    from .energy_market_impact import build_energy_market_impact_cards, build_energy_scenario_evidence

    return {
        "impact_cards": build_energy_market_impact_cards(energy_payload, macro_payload),
        "scenario_evidence": build_energy_scenario_evidence(energy_payload, macro_payload),
        "caveat": "Energy market impact context uses proxy reaction and potential-channel language only.",
    }
