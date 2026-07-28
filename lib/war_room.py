from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .country_risk_model import build_country_risk_cards, build_country_risk_table
from .data_status import DataResult, combine_results, error_result, get_recent_results, ok_result, provider_status_table
from .event_stream import build_event_feed_cards, build_event_stream, build_event_timeline
from .env_loader import get_env_var
from .geo_layers import build_chokepoint_layer, build_layered_event_map
from .intelligence_scoring import build_hotspot_leaderboard, build_intelligence_watchpoints
from .layer_registry import build_layer_registry, build_layer_runtime_payload, get_default_layers, layer_status_table
from .live_feeds import build_keyless_runtime_feeds
from .provider_health_engine import build_provider_health_snapshot
from .source_freshness import source_freshness_table

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
    return []


def _frame(rows: list[dict[str, Any]]):
    return pd.DataFrame(rows) if pd is not None else rows


def _risk_state(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 45:
        return "elevated"
    if score >= 20:
        return "watch"
    return "low"


def _status_value(status: DataResult | None) -> str:
    return status.refreshed_status() if status is not None else "unknown"


def build_war_room_header_metrics(state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or {}
    hotspots = state.get("hotspot_leaderboard")
    top_score = 0.0
    if hotspots is not None and hasattr(hotspots, "empty") and not hotspots.empty and "score" in hotspots.columns:
        top_score = float(hotspots["score"].max())
    elif isinstance(hotspots, list) and hotspots:
        top_score = max(float(item.get("score", 0)) for item in hotspots)
    layers = state.get("layers") or build_layer_registry()
    available_layers = sum(1 for layer in layers if layer.get("is_available"))
    optional_layers = sum(1 for layer in layers if layer.get("is_optional"))
    statuses = _records(state.get("source_status"))
    missing_sources = sum(1 for item in statuses if str(item.get("status")).lower() in {"missing", "error"})
    now_utc = datetime.now(timezone.utc)
    return {
        "title": "Global War Room",
        "utc_timestamp": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "local_timestamp": now_utc.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "global_risk_state": _risk_state(top_score),
        "global_risk_score": round(top_score, 1),
        "available_layers": available_layers,
        "optional_layers": optional_layers,
        "missing_or_error_sources": missing_sources,
        "data_freshness_summary": "data gap" if missing_sources else "available/estimated",
        "command_modes": ["Global", "Equity", "Crypto", "Energy", "Geopolitics", "Chokepoints", "Korea", "Custom"],
    }


def build_global_event_map(events: Any = None):
    from .geo_layers import build_global_event_map as _build_global_event_map

    return _build_global_event_map(events)


def compute_country_instability_score(country: str, events: Any = None) -> dict[str, Any]:
    from .country_risk_model import compute_country_instability_score as _compute_country_instability_score

    return _compute_country_instability_score(country, events)


def compute_signal_convergence(**kwargs: Any) -> dict[str, Any]:
    from .intelligence_scoring import compute_signal_convergence as _compute_signal_convergence

    return _compute_signal_convergence(**kwargs)


def build_war_room_map_payload(events: Any = None, layers: list[str] | None = None) -> dict[str, Any]:
    selected_layers = layers or get_default_layers()
    fig, frame, status = build_layered_event_map(events, selected_layers)
    choke_fig, choke_frame, choke_status = build_chokepoint_layer()
    return {
        "fig": fig,
        "frame": frame,
        "status": status,
        "selected_layers": selected_layers,
        "chokepoint_fig": choke_fig,
        "chokepoint_frame": choke_frame,
        "chokepoint_status": choke_status,
        "caveat": "Map uses source-backed coordinates or clearly marked approximate centroids; route/chokepoint layers are proxies.",
    }


def build_war_room_market_impact_summary(events: Any = None) -> dict[str, Any]:
    rows = _records(events)
    asset_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}
    for event in rows:
        domain = str(event.get("domain") or "unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        for ticker in event.get("related_tickers") or event.get("related_assets") or []:
            asset_counts[str(ticker)] = asset_counts.get(str(ticker), 0) + 1
    ranked_assets = sorted(asset_counts.items(), key=lambda item: item[1], reverse=True)
    ranked_domains = sorted(domain_counts.items(), key=lambda item: item[1], reverse=True)
    return {
        "top_related_assets": [{"ticker": ticker, "event_count": count, "label": "potential channel"} for ticker, count in ranked_assets[:12]],
        "domain_mix": [{"domain": domain, "event_count": count} for domain, count in ranked_domains],
        "stress_bar": min(100, sum(count for _, count in ranked_assets[:6]) * 8),
        "caveat": "Market impact summary is event linkage and proxy/correlation context only.",
    }


def build_war_room_source_status(statuses: list[DataResult] | None = None):
    recent = statuses if statuses is not None else get_recent_results()
    table = source_freshness_table(recent)
    if table is None or getattr(table, "empty", True):
        table = _frame(
            [
                {
                    "provider": "war_room",
                    "source": "runtime status",
                    "status": "missing",
                    "age_minutes": None,
                    "coverage": "No prior data status records in this session.",
                    "estimated": True,
                    "cached": False,
                    "paid_required": False,
                    "warning": "Run data views to populate recent status telemetry.",
                    "error": None,
                }
            ]
        )
    return table


def build_war_room_right_rail(events: Any = None, statuses: list[DataResult] | None = None) -> dict[str, Any]:
    event_cards = build_event_feed_cards(events, limit=10)
    country_cards = build_country_risk_cards(events, limit=6)
    hotspots = build_hotspot_leaderboard(events)
    watchpoints = build_intelligence_watchpoints(events, limit=8)
    source_status = build_war_room_source_status(statuses)
    return {
        "event_cards": event_cards,
        "country_cards": country_cards,
        "hotspots": hotspots,
        "watchpoints": watchpoints,
        "source_status": source_status,
        "ai_brief": {
            "title": "AI brief context",
            "sections": ["What changed", "Related market channels", "Observed proxy reactions", "Scenario watch-points", "Uncertainty", "Data gaps"],
            "caveat": "AI summary; verify primary data. Not financial advice.",
        },
    }


def build_war_room_macro_energy_payload(*, include_live: bool = False) -> dict[str, Any]:
    from .macro_regime_engine import build_macro_regime_cards
    from .shipping_chokepoint_engine import build_chokepoint_risk_cards, compute_shipping_disruption_proxy

    macro_cards = build_macro_regime_cards({}) if not include_live else []
    energy_card = {
        "label": "Energy Risk Proxy",
        "value": "static/proxy",
        "score": compute_shipping_disruption_proxy()["shipping_disruption_proxy"],
        "source_confidence": 45,
        "data_gaps": ["EIA/OpenBB/AIS are optional and not queried by default in War Room."],
        "caveat": "Energy and chokepoint rail is proxy-labeled unless explicit providers are configured.",
    }
    chokepoint_cards = build_chokepoint_risk_cards()
    if include_live:
        try:
            from .openbb_energy_backend import build_energy_dashboard_payload
            from .openbb_macro_backend import build_macro_rates_dashboard_payload

            macro_payload = build_macro_rates_dashboard_payload(source_mode="auto")
            macro_cards = build_macro_regime_cards(macro_payload)
            energy_payload = build_energy_dashboard_payload(source_mode="auto")
            energy_card["source_confidence"] = energy_payload.get("source_confidence", 0)
            energy_card["data_gaps"] = [getattr(gap, "field", str(gap)) for gap in energy_payload.get("data_gaps", [])]
        except Exception as exc:
            energy_card["data_gaps"].append(f"Unified live payload unavailable: {exc}")
    return {
        "macro_cards": macro_cards,
        "energy_cards": [energy_card],
        "chokepoint_cards": chokepoint_cards,
        "route_exposure_layer": chokepoint_cards,
        "country_region_macro_stress": macro_cards,
        "caveat": "War Room macro/energy cards are informational and proxy-labeled where source data is unavailable.",
    }


def build_war_room_ai_context(state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or {}
    events = _records(state.get("events"))
    market_summary = state.get("market_impact_summary") or build_war_room_market_impact_summary(events)
    country_table = state.get("country_risk_table")
    country_rows = country_table.head(8).to_dict(orient="records") if hasattr(country_table, "head") else _records(country_table)[:8]
    return {
        "ai_summary": "Use neutral market/intelligence language only.",
        "what_changed": events[:12],
        "related_market_channels": market_summary,
        "country_risk": country_rows,
        "scenario_watchpoints": state.get("right_rail", {}).get("watchpoints", []),
        "uncertainty": "Public feeds may be delayed, duplicated, stale, or missing coordinates.",
        "data_gaps": [
            "No live AIS or military flight tracking provider is configured.",
            "Country instability scores are heuristic.",
            "Optional WorldMonitor adapter requires explicit configuration.",
        ],
        "not_financial_advice": True,
        "verify_primary_data": True,
    }


def build_war_room_state(
    *,
    news: Any = None,
    market: Any = None,
    crypto: Any = None,
    energy: Any = None,
    chokepoints: Any = None,
    natural: Any = None,
    flight: Any = None,
    layers: list[str] | None = None,
    statuses: list[DataResult] | None = None,
    include_default_runtime: bool | None = None,
) -> dict[str, Any]:
    runtime_payload: dict[str, Any] | None = None
    should_fetch_runtime = (
        bool(include_default_runtime)
        if include_default_runtime is not None
        else all(value is None for value in [news, market, crypto, energy, chokepoints, natural, flight])
    )
    runtime_statuses: list[DataResult] = []
    if should_fetch_runtime:
        include_flights = bool(get_env_var("OPENSKY_CLIENT_ID") and get_env_var("OPENSKY_CLIENT_SECRET"))
        runtime_payload = build_keyless_runtime_feeds(include_flights=include_flights)
        if news is None:
            news = runtime_payload.get("news")
        if crypto is None:
            crypto = runtime_payload.get("crypto")
        if natural is None:
            natural = runtime_payload.get("natural")
        if flight is None:
            flight = runtime_payload.get("flight")
        runtime_statuses = [item for item in runtime_payload.get("source_statuses", []) if isinstance(item, DataResult)]
    layer_rows = build_layer_registry()
    event_rows = build_event_stream(news=news, market=market, crypto=crypto, energy=energy, chokepoints=chokepoints, natural=natural, flight=flight)
    layer_status = layer_status_table(layer_rows)
    combined_statuses = list(statuses or []) + runtime_statuses
    source_status = build_war_room_source_status(combined_statuses)
    provider_health = build_provider_health_snapshot(combined_statuses)
    country_table = build_country_risk_table(event_rows)
    map_payload = build_war_room_map_payload(event_rows, layers)
    timeline = build_event_timeline(event_rows)
    right_rail = build_war_room_right_rail(event_rows, combined_statuses)
    market_summary = build_war_room_market_impact_summary(event_rows)
    runtime_state_payload = None
    if runtime_payload is not None:
        runtime_state_payload = {
            **runtime_payload,
            "source_statuses": [status.to_dict() for status in runtime_statuses],
        }
    layer_runtime_status = build_layer_runtime_payload(runtime_payload, combined_statuses, layer_rows)
    state = {
        "layers": layer_rows,
        "layer_status": layer_status,
        "layer_runtime_status": layer_runtime_status,
        "events": event_rows,
        "event_frame": _frame(event_rows),
        "event_timeline": timeline,
        "country_risk_table": country_table,
        "map_payload": map_payload,
        "right_rail": right_rail,
        "market_impact_summary": market_summary,
        "macro_energy_payload": build_war_room_macro_energy_payload(include_live=False),
        "source_status": source_status,
        "provider_health_ledger": provider_health,
        "runtime_feeds": runtime_state_payload
        or {
            "news": [],
            "natural": [],
            "crypto": [],
            "flight": [],
            "source_statuses": [status.to_dict() for status in combined_statuses],
            "data_gaps": [],
            "caveat": "Runtime feed fetch was not requested for this state build.",
        },
        "hotspot_leaderboard": right_rail["hotspots"],
        "worldmonitor_adapter_status": "configured" if any(layer["layer_id"] == "worldmonitor_optional_adapter" and layer["is_available"] for layer in layer_rows) else "not configured",
        "caveat": "War Room combines real available data, static registries, and clearly marked heuristic/proxy layers.",
    }
    state["header_metrics"] = build_war_room_header_metrics(state)
    state["ai_context"] = build_war_room_ai_context(state)
    statuses_for_result = [map_payload.get("status"), map_payload.get("chokepoint_status")] + combined_statuses
    state["status"] = combine_results([status for status in statuses_for_result if status is not None], provider="war_room", source="war room state")
    return state


def build_data_gap_panel(state: dict[str, Any] | None = None):
    state = state or {}
    gaps = []
    for event in _records(state.get("events")):
        if event.get("data_gap"):
            gaps.append({"area": event.get("domain"), "gap": event.get("data_gap"), "event": event.get("title")})
    if not gaps:
        gaps.append({"area": "runtime", "gap": "No explicit event data gaps beyond optional unavailable feeds.", "event": None})
    return _frame(gaps)
