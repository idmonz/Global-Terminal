from __future__ import annotations

from typing import Any, Iterable

from .click_path_engine import build_page_next_actions
from .summary_keyword_engine import extract_summary_keywords

from .market_radar import (
    build_crypto_derivatives_radar,
    build_energy_risk_radar,
    build_equity_breadth_radar,
    build_market_composite_score,
    build_volatility_radar,
)

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def _card(
    title: str,
    summary: str,
    *,
    severity: str = "watch",
    tags: Iterable[str] | None = None,
    source: str = "heuristic proxy",
    freshness: str = "estimated",
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "summary": summary,
        "severity": severity,
        "tags": list(tags or []),
        "source": source,
        "freshness": freshness,
        "metrics": metrics or {},
        "method": "heuristic" if "heuristic" in source.lower() or "proxy" in source.lower() else "source-derived",
    }


def _first_record(frame: Any) -> dict[str, Any]:
    if hasattr(frame, "to_dict") and not getattr(frame, "empty", True):
        return frame.to_dict(orient="records")[0]
    if isinstance(frame, list) and frame:
        return frame[0]
    return {}


def build_market_intelligence_cards(payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = payload or {}
    equity_radar = build_equity_breadth_radar(payload.get("equity") if isinstance(payload.get("equity"), dict) else {})
    vol_radar = build_volatility_radar(payload.get("risk") if isinstance(payload.get("risk"), dict) else {}, payload.get("cards"))
    composite = build_market_composite_score(equity_radar, vol_radar)
    equity = _first_record(equity_radar)
    vol = _first_record(vol_radar)
    return [
        _card(
            "Cross-Asset Composite",
            f"{composite['label']} across {composite['components']} available radar components.",
            severity="medium" if composite["score"] >= 60 else "watch",
            tags=["cross-asset", "composite"],
            metrics={"score": composite["score"]},
        ),
        _card(
            "Equity Breadth",
            equity.get("label", "Data gap"),
            severity="medium" if equity.get("score", 0) >= 60 else "watch",
            tags=["equity", "breadth"],
            metrics={"score": equity.get("score")},
        ),
        _card(
            "Volatility Regime",
            vol.get("label", "Data gap"),
            severity="medium" if vol.get("score", 0) >= 55 else "watch",
            tags=["risk", "volatility"],
            metrics={"score": vol.get("score")},
        ),
    ]


def build_crypto_intelligence_cards(snapshot: dict[str, Any] | None = None, pressure_map: Any = None) -> list[dict[str, Any]]:
    radar = _first_record(build_crypto_derivatives_radar(snapshot, pressure_map))
    snapshot = snapshot or {}
    return [
        _card(
            "Derivatives Radar",
            radar.get("label", "Data gap"),
            severity="medium" if radar.get("score", 0) >= 55 else "watch",
            tags=["crypto", "derivatives", "proxy"],
            source="Binance/public derivatives where available; heuristic proxy",
            metrics={"score": radar.get("score"), "funding_rate": snapshot.get("funding_rate")},
        ),
        _card(
            "Positioning Context",
            "Long/short and taker ratios are treated as crowding evidence, not direction advice.",
            severity="watch",
            tags=["positioning", "crowding"],
            source="public derivatives snapshot",
            metrics={
                "global_long_short_ratio": snapshot.get("global_long_short_ratio"),
                "taker_ratio": snapshot.get("taker_buy_sell_ratio"),
            },
        ),
    ]


def build_energy_intelligence_cards(energy: dict[str, Any] | None = None, news_risk: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    radar = _first_record(build_energy_risk_radar(energy, news_risk))
    energy = energy or {}
    return [
        _card(
            "Energy Risk Radar",
            radar.get("label", "Data gap"),
            severity="high" if radar.get("score", 0) >= 75 else "medium" if radar.get("score", 0) >= 55 else "watch",
            tags=["energy", "geopolitical", "proxy"],
            source="static chokepoints plus public news proxy",
            metrics={"score": radar.get("score")},
        ),
        _card(
            "Chokepoint Watch",
            str(energy.get("chokepoint_risk_proxy") or "Static chokepoint registry; no live vessel flow."),
            severity="medium",
            tags=["shipping", "oil", "AIS unavailable"],
            source="static registry",
            freshness="estimated",
        ),
    ]


def build_risk_intelligence_cards(risk: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    risk = risk or {}
    return [
        _card(
            "Risk Stack",
            str(risk.get("cross_asset_volatility_regime") or "Mixed evidence"),
            severity="medium" if str(risk.get("cross_asset_volatility_regime", "")).lower().startswith("elevated") else "watch",
            tags=risk.get("risk_scenario_badges") or ["volatility", "correlation"],
            source="overview risk proxy",
            metrics={"vix": risk.get("vix")},
        )
    ]


def build_news_intelligence_cards(news_dashboard: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    news_dashboard = news_dashboard or {}
    high = news_dashboard.get("high_severity_feed")
    if hasattr(high, "head"):
        records = high.head(4).to_dict(orient="records")
    elif isinstance(high, list):
        records = high[:4]
    else:
        records = []
    if not records:
        return [
            _card(
                "News Intelligence",
                "No high-severity public feed items are available in the current payload.",
                severity="watch",
                tags=["news", "data gap"],
                source="public feed dashboard",
                freshness="missing",
            )
        ]
    return [
        _card(
            str(row.get("title") or "News watch-point"),
            str(row.get("summary") or row.get("description") or "Heuristic classification."),
            severity=str(row.get("severity") or "watch"),
            tags=(row.get("impact_channels") or []) + (row.get("asset_tags") or []) if isinstance(row.get("asset_tags"), list) else row.get("impact_channels") or [],
            source=str(row.get("source") or "public feed"),
            freshness=str(row.get("freshness") or "unknown"),
            metrics={"severity_score": row.get("severity_score")},
        )
        for row in records
    ]


def build_ai_brief_card(response: Any = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    provider = getattr(response, "provider", None) or (context or {}).get("provider") or "rule_based"
    model = getattr(response, "model", None) or (context or {}).get("model") or "deterministic-neutral-fallback"
    ok = getattr(response, "ok", True)
    return _card(
        "AI Situational Brief",
        "Button-triggered neutral summary. Provider output is treated as analyst support, not ground truth.",
        severity="watch" if ok else "medium",
        tags=["AI", provider, model],
        source="configured AI provider" if provider != "rule_based" else "offline rule-based fallback",
        freshness="estimated",
        metrics={"provider": provider, "model": model, "ok": ok},
    )


def build_data_gap_cards(gaps: Iterable[Any] | None = None, statuses: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    cards = []
    for gap in gaps or []:
        cards.append(
            _card(
                "Data Gap",
                str(gap),
                severity="watch",
                tags=["data gap"],
                source="dashboard status",
                freshness="missing",
            )
        )
    for status in statuses or []:
        if getattr(status, "ok", True):
            continue
        cards.append(
            _card(
                "Source Gap",
                getattr(status, "error", None) or "Source unavailable.",
                severity="medium",
                tags=[getattr(status, "provider", "source")],
                source=getattr(status, "source", "source status"),
                freshness="missing",
            )
        )
    return cards or [
        _card(
            "Data Coverage",
            "No blocking data gaps were reported by this builder.",
            severity="low",
            tags=["coverage"],
            source="dashboard status",
            freshness="fresh",
        )
    ]


def build_summary_first_intelligence_deck(page: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return {
        "page": page,
        "summary": payload.get("summary") or "Summary-first research context with explicit source and data-quality labels.",
        "keywords": extract_summary_keywords(payload),
        "next_actions": build_page_next_actions(page, payload),
        "cards": build_market_intelligence_cards(payload) + build_data_gap_cards(payload.get("data_gaps"), payload.get("source_statuses")),
    }
