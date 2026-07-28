from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .research_report_workstation import find_forbidden_report_phrases
from .research_workspace_db import get_connection


DAILY_BRIEF_VERSION = "daily_brief.v1"
CAPTURE_VERSION = "daily_brief_capture.v1"
BRIEF_ID_PATTERN = re.compile(r"^brief_[a-f0-9]{20}$")
PERIODS = {"morning", "midday", "close", "weekly"}
RUNTIME_MODES = {"fixture", "cache", "live-if-available", "local"}
REVIEW_STATUSES = {"unread", "reviewed", "archived"}
PRIVATE_KEYS = {
    "access_token", "api_key", "authorization", "client_secret", "password", "private_body",
    "prompt", "raw_payload", "review_notes", "token", "watch_reason", "db_path", "local_path",
}
VOLATILE_FIELDS = {"fetched_at", "generated_at", "captured_at", "reviewed_at", "retention_until"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _text(value: Any, *, limit: int = 1200, fallback: str = "") -> str:
    text = str(value if value is not None else fallback).replace("\x00", "").strip()
    return (text or fallback)[:limit]


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return []


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value) if value not in {None, ""} else fallback
    except (TypeError, ValueError):
        return fallback


def _stable_id(prefix: str, *parts: Any) -> str:
    encoded = "|".join(_text(part, limit=500).lower() for part in parts)
    return f"{prefix}_{hashlib.sha256(encoded.encode('utf-8')).hexdigest()[:20]}"


def _status(row: dict[str, Any], fallback: str = "unknown") -> str:
    return _text(row.get("source_status") or row.get("status") or row.get("freshness"), fallback=fallback).lower()


def _confidence(row: dict[str, Any], status: str) -> float:
    try:
        return max(0.0, min(1.0, float(row.get("confidence"))))
    except (TypeError, ValueError):
        return {
            "live/fresh": 0.86, "cached": 0.72, "stale": 0.5, "fixture": 0.35,
            "proxy/static": 0.3, "missing-key": 0.0, "unavailable": 0.0,
        }.get(status, 0.45)


def _privacy_scope(row: dict[str, Any]) -> str:
    explicit = _text(row.get("privacy_scope"), limit=40)
    if explicit:
        return explicit
    provider = _text(row.get("provider") or row.get("source"), limit=120).lower()
    return "local-private" if any(token in provider for token in ("watchlist", "local-private", "manual-note")) else "public"


def _source_row(row: dict[str, Any], *, provider_fallback: str, source_fallback: str) -> dict[str, Any]:
    provider = _text(row.get("provider") or provider_fallback, limit=120, fallback=provider_fallback)
    source = _text(row.get("source") or source_fallback, limit=300, fallback=source_fallback)
    source_url = _text(row.get("source_url") or row.get("url"), limit=1000) or None
    status = _status(row)
    observed_at = _text(
        row.get("observed_at") or row.get("timestamp") or row.get("published_at") or row.get("market_as_of"),
        limit=80,
    ) or None
    return {
        "source_id": _stable_id("source", provider, source_url or source),
        "provider": provider,
        "source": source,
        "source_url": source_url,
        "fetched_at": _text(row.get("fetched_at") or row.get("latest_fetched_at"), limit=80) or None,
        "observed_at": observed_at,
        "freshness": _text(row.get("freshness") or status, limit=80, fallback=status),
        "source_status": status,
        "confidence": _confidence(row, status),
        "caveat": _text(row.get("caveat"), fallback="Inspect source status before relying on this observation."),
        "data_gap": _text(row.get("data_gap") or row.get("error") or row.get("warning"), fallback="No additional data gap reported."),
        "privacy_scope": _privacy_scope(row),
        "not_financial_advice": True,
    }


def _claim(
    *,
    claim_kind: str,
    identity: str,
    statement: str,
    source: dict[str, Any],
    section_id: str,
    severity: str = "context",
    linked_symbols: Iterable[Any] = (),
    linked_regions: Iterable[Any] = (),
    linked_events: Iterable[Any] = (),
    data_gap: str | None = None,
) -> dict[str, Any]:
    return {
        "claim_id": _stable_id("claim", claim_kind, identity),
        "claim_kind": claim_kind,
        "section_id": section_id,
        "statement": _text(statement),
        "source_ids": [source["source_id"]],
        "provider": source["provider"],
        "source_status": source["source_status"],
        "freshness": source["freshness"],
        "fetched_at": source["fetched_at"],
        "observed_at": source["observed_at"],
        "confidence": source["confidence"],
        "severity": severity,
        "linked_symbols": sorted({_text(item, limit=40).upper() for item in linked_symbols if _text(item)}),
        "linked_regions": sorted({_text(item, limit=120) for item in linked_regions if _text(item)}),
        "linked_events": sorted({_text(item, limit=120) for item in linked_events if _text(item)}),
        "caveat": source["caveat"],
        "data_gap": _text(data_gap or source["data_gap"]),
        "privacy_scope": source["privacy_scope"],
        "not_financial_advice": True,
    }


def _safe_number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _market_claims(rows: list[dict[str, Any]], register: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda row: abs(_safe_number(row.get("daily_return_pct")) or 0.0), reverse=True)[:6]
    claims = []
    for row in ranked:
        symbol = _text(row.get("symbol"), limit=40).upper()
        if not symbol:
            continue
        source = _source_row(row, provider_fallback="market-provider", source_fallback=f"{symbol} market observation")
        register[source["source_id"]] = source
        daily = _safe_number(row.get("daily_return_pct"))
        monthly = _safe_number(row.get("one_month_return_pct"))
        daily_text = "unavailable" if daily is None else f"{daily:+.2f}%"
        monthly_text = "unavailable" if monthly is None else f"{monthly:+.2f}%"
        severity = "elevated" if daily is not None and abs(daily) >= 1.0 else "context"
        claims.append(_claim(
            claim_kind="market_observation", identity=symbol,
            statement=f"{symbol} recorded a {daily_text} supplied-window change; the supplied one-month change is {monthly_text}.",
            source=source, section_id="cross_asset", severity=severity, linked_symbols=[symbol],
        ))
    return claims


def _event_claims(rows: list[dict[str, Any]], register: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda row: _safe_number(row.get("severity_score")) or 0.0, reverse=True)[:6]
    claims = []
    for row in ranked:
        identity = _text(row.get("marker_id") or row.get("event_id") or row.get("source_url") or row.get("title"))
        if not identity:
            continue
        source = _source_row(row, provider_fallback="event-provider", source_fallback="global risk observation")
        register[source["source_id"]] = source
        region = _text(row.get("region") or row.get("location"), fallback="unspecified region")
        severity = _text(row.get("severity"), limit=40, fallback="watch")
        symbols = [str(item).split(":")[-1].upper() for item in list(row.get("related_asset_node_ids") or [])[:12]]
        claims.append(_claim(
            claim_kind="global_risk_observation", identity=identity,
            statement=f"{_text(row.get('title'), fallback='A global-risk event')} is recorded for {region} with {severity} severity.",
            source=source, section_id="global_risk", severity=severity, linked_symbols=symbols,
            linked_regions=[region], linked_events=[identity],
            data_gap="; ".join(part for part in [source["data_gap"], "Temporal proximity does not establish market causality."] if part),
        ))
    return claims


def _news_claims(rows: list[dict[str, Any]], register: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    claims = []
    seen: set[str] = set()
    for row in rows[:10]:
        identity = _text(row.get("source_url") or row.get("url") or row.get("event_id") or row.get("title"))
        if not identity or identity in seen:
            continue
        seen.add(identity)
        source = _source_row(row, provider_fallback="news-provider", source_fallback="public news observation")
        register[source["source_id"]] = source
        region = _text(row.get("region") or row.get("location"))
        claims.append(_claim(
            claim_kind="news_observation", identity=identity,
            statement=f"A source report records: {_text(row.get('title'), fallback='untitled public report')}.",
            source=source, section_id="news_flow", severity=_text(row.get("severity"), limit=40, fallback="context"),
            linked_symbols=list(row.get("related_assets") or [])[:12], linked_regions=[region] if region else (),
        ))
    return claims


def _provider_gap_claims(rows: list[dict[str, Any]], register: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    gap_statuses = {
        "configured-unverified", "missing-key", "provider-required", "unavailable",
        "forbidden/subscription-blocked", "rate-limited", "stale",
    }
    claims = []
    for row in rows[:40]:
        status = _status(row)
        if status not in gap_statuses and _text(row.get("availability")).lower() != "unavailable":
            continue
        provider = _text(row.get("provider"), limit=120, fallback="unknown provider")
        source = _source_row(row, provider_fallback=provider, source_fallback=f"{provider} readiness")
        register[source["source_id"]] = source
        claims.append(_claim(
            claim_kind="gap", identity=f"{provider}:{status}",
            statement=f"{provider} coverage is {status}; the brief does not substitute synthetic live data.",
            source=source, section_id="data_quality", severity="gap", data_gap=source["data_gap"],
        ))
    return claims


def _watchlist_claims(rows: list[dict[str, Any]], register: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    claims = []
    for row in rows[:30]:
        symbol = _text(row.get("symbol"), limit=40).upper()
        label = symbol or _text(row.get("display_name"), limit=120)
        if not label:
            continue
        source = _source_row(
            {"provider": "local-watchlist", "source": "Local watchlist context", "source_status": "local-private", "freshness": "local", "confidence": 1.0, "privacy_scope": "local-private", "caveat": "Private watchlist metadata is not transmitted to external AI.", "data_gap": "Watchlist membership is context, not a market signal."},
            provider_fallback="local-watchlist", source_fallback="Local watchlist context",
        )
        register[source["source_id"]] = source
        claims.append(_claim(
            claim_kind="watchlist_context", identity=label,
            statement=f"{label} is present in the local research watchlist context.",
            source=source, section_id="watchlist", linked_symbols=[symbol] if symbol else (),
        ))
    return claims


def _section(section_id: str, title: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in claims if row["section_id"] == section_id]
    claim_ids = [row["claim_id"] for row in rows]
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["source_status"]] = status_counts.get(row["source_status"], 0) + 1
    if not rows:
        sentence = "No source-bound claims are available for this section."
    elif section_id == "data_quality":
        sentence = f"{len(rows)} provider or freshness gaps require explicit review."
    else:
        sentence = f"{len(rows)} source-bound observations are available in {title.lower()}."
    return {
        "section_id": section_id,
        "title": title,
        "claim_ids": claim_ids,
        "material_sentences": [{"text": sentence, "claim_ids": claim_ids}],
        "source_status_counts": dict(sorted(status_counts.items())),
        "confidence": round(sum(float(row["confidence"]) for row in rows) / max(1, len(rows)), 3),
        "caveat": "Section text is deterministically composed from the listed claim IDs.",
        "not_financial_advice": True,
    }


def _chart_point_count(chart: dict[str, Any]) -> int:
    return sum(len(_records(series.get("points"))) for series in _records(chart.get("series")))


def _chart_panels(
    market_data: dict[str, Any],
    claims: list[dict[str, Any]],
    register: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    panels: list[dict[str, Any]] = []
    cross_asset_claims = [row for row in claims if row.get("section_id") == "cross_asset"]
    default_claim_ids = [row["claim_id"] for row in cross_asset_claims[:6]]
    linked_symbols = sorted({symbol for row in cross_asset_claims for symbol in row.get("linked_symbols", [])})
    for chart in _records(market_data.get("chart_specs"))[:4]:
        chart_id = _text(chart.get("chart_id") or chart.get("title"), limit=120)
        if not chart_id:
            continue
        source = _source_row(
            chart,
            provider_fallback="chart-spec",
            source_fallback=_text(chart.get("title"), fallback="Daily brief chart evidence"),
        )
        register[source["source_id"]] = source
        point_count = _chart_point_count(chart)
        panels.append(
            {
                "chart_panel_id": _stable_id("chart_panel", chart_id),
                "chart_id": chart_id,
                "title": _text(chart.get("title"), fallback=chart_id),
                "chart_type": _text(chart.get("chart_type"), limit=40, fallback="bar"),
                "unit": _text(chart.get("unit"), limit=40),
                "source_ids": [source["source_id"]],
                "claim_ids": default_claim_ids,
                "linked_symbols": linked_symbols[:12],
                "point_count": point_count,
                "chart_spec": chart,
                "primary_drilldowns": [
                    {"label": "Open Market Intelligence", "href": "/?view=market-intelligence&mode=cache"},
                    *[
                        {
                            "label": symbol,
                            "href": f"/?view=asset&symbol={symbol}&assetClass={'crypto' if symbol.endswith('USDT') or symbol.endswith('-USD') else 'equity'}&mode=cache",
                        }
                        for symbol in linked_symbols[:4]
                    ],
                ],
                "provider": source["provider"],
                "source_status": source["source_status"],
                "freshness": source["freshness"],
                "fetched_at": source["fetched_at"],
                "confidence": source["confidence"],
                "caveat": _text(chart.get("caveat") or source["caveat"]),
                "data_gap": _text(chart.get("data_gap") or source["data_gap"]),
                "not_financial_advice": True,
            }
        )
    return panels


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = _text(row.get("source_status"), limit=80, fallback="unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _perspective(
    *,
    perspective_id: str,
    role: str,
    title: str,
    rows: list[dict[str, Any]],
    empty_data_gap: str,
) -> dict[str, Any] | None:
    if not rows:
        return None
    claim_ids = [row["claim_id"] for row in rows[:8]]
    source_ids = sorted({source_id for row in rows for source_id in list(row.get("source_ids") or []) if _text(source_id)})
    statuses = {row.get("source_status") for row in rows}
    gap_count = sum(row.get("claim_kind") == "gap" for row in rows)
    avg_confidence = round(sum(float(row.get("confidence") or 0.0) for row in rows) / max(1, len(rows)), 3)
    stance = "coverage-limited" if gap_count else ("evidence-available" if statuses & {"live/fresh", "cached"} else "evidence-light")
    emphasis = "weakening evidence review" if gap_count else "supporting and contrary evidence review"
    return {
        "perspective_id": perspective_id,
        "role": role,
        "title": title,
        "stance": stance,
        "evidence_mode": emphasis,
        "claim_ids": claim_ids,
        "source_ids": source_ids,
        "supporting_claim_ids": [row["claim_id"] for row in rows if row.get("claim_kind") != "gap"][:5],
        "weakening_claim_ids": [row["claim_id"] for row in rows if row.get("claim_kind") == "gap"][:5],
        "source_status_counts": _status_counts(rows),
        "confidence": avg_confidence,
        "summary": f"{len(rows)} source-bound observations reviewed by the {role}; stance is {stance}.",
        "clean_room_reference": "TradingAgents analyst-role pattern, behavior-only clean-room reconstruction; no external source copied.",
        "data_gap": empty_data_gap if not source_ids else "Perspective uses only the referenced claim and source IDs.",
        "caveat": "Perspective is a deterministic research lens, not a directional recommendation or account-action instruction.",
        "not_financial_advice": True,
    }


def _research_perspectives(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = [
        (
            "perspective_cross_asset",
            "cross_asset_researcher",
            "Cross-Asset Evidence Lens",
            [row for row in claims if row.get("section_id") == "cross_asset"],
            "No cross-asset source-bound claims are available.",
        ),
        (
            "perspective_global_risk",
            "global_risk_researcher",
            "Global Risk And Map Lens",
            [row for row in claims if row.get("section_id") == "global_risk"],
            "No source-bound map or event claims are available.",
        ),
        (
            "perspective_news_flow",
            "news_flow_researcher",
            "News Flow Lens",
            [row for row in claims if row.get("section_id") == "news_flow"],
            "No source-bound public news claims are available.",
        ),
        (
            "perspective_data_quality",
            "data_quality_reviewer",
            "Source Coverage Lens",
            [row for row in claims if row.get("section_id") == "data_quality" or row.get("claim_kind") == "gap"],
            "No provider health or source-gap claims are available.",
        ),
    ]
    return [row for row in (_perspective(perspective_id=pid, role=role, title=title, rows=rows, empty_data_gap=gap) for pid, role, title, rows, gap in groups) if row]


def _overall_status(sources: list[dict[str, Any]]) -> str:
    statuses = {row["source_status"] for row in sources}
    if not statuses:
        return "unavailable"
    if statuses == {"fixture"}:
        return "fixture"
    if "live/fresh" in statuses and len(statuses) == 1:
        return "live/fresh"
    if statuses <= {"local-private", "local"}:
        return "local-private"
    return "mixed"


def validate_daily_brief(brief: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    sources = _records(brief.get("source_register"))
    claims = _records(brief.get("claims"))
    sections = _records(brief.get("sections"))
    chart_panels = _records(brief.get("chart_panels"))
    perspectives = _records(brief.get("research_perspectives"))
    source_ids = {_text(row.get("source_id")) for row in sources}
    claim_ids = {_text(row.get("claim_id")) for row in claims}
    for claim in claims:
        refs = {_text(item) for item in list(claim.get("source_ids") or []) if _text(item)}
        if not refs:
            issues.append(f"{claim.get('claim_id')}: missing source IDs")
        elif not refs <= source_ids:
            issues.append(f"{claim.get('claim_id')}: unknown source ID")
        issues.extend(f"{claim.get('claim_id')}: forbidden phrase {phrase}" for phrase in find_forbidden_report_phrases(claim.get("statement")))
    for section in sections:
        refs = {_text(item) for item in list(section.get("claim_ids") or []) if _text(item)}
        if not refs <= claim_ids:
            issues.append(f"{section.get('section_id')}: unknown claim ID")
        for sentence in _records(section.get("material_sentences")):
            if sentence.get("text") and not sentence.get("claim_ids") and refs:
                issues.append(f"{section.get('section_id')}: material sentence missing claim IDs")
    for panel in chart_panels:
        refs = {_text(item) for item in list(panel.get("source_ids") or []) if _text(item)}
        claim_refs = {_text(item) for item in list(panel.get("claim_ids") or []) if _text(item)}
        if not refs or not refs <= source_ids:
            issues.append(f"{panel.get('chart_panel_id')}: chart panel has unknown source IDs")
        if claim_refs and not claim_refs <= claim_ids:
            issues.append(f"{panel.get('chart_panel_id')}: chart panel has unknown claim IDs")
        if int(panel.get("point_count") or 0) < 1:
            issues.append(f"{panel.get('chart_panel_id')}: chart panel has no plotted points")
        issues.extend(f"{panel.get('chart_panel_id')}: forbidden phrase {phrase}" for phrase in find_forbidden_report_phrases(panel))
    for perspective in perspectives:
        refs = {_text(item) for item in list(perspective.get("source_ids") or []) if _text(item)}
        claim_refs = {_text(item) for item in list(perspective.get("claim_ids") or []) if _text(item)}
        if not refs or not refs <= source_ids:
            issues.append(f"{perspective.get('perspective_id')}: perspective has unknown source IDs")
        if not claim_refs or not claim_refs <= claim_ids:
            issues.append(f"{perspective.get('perspective_id')}: perspective has unknown claim IDs")
        issues.extend(f"{perspective.get('perspective_id')}: forbidden phrase {phrase}" for phrase in find_forbidden_report_phrases(perspective))
    return {"valid": not issues, "issues": sorted(set(issues)), "claim_count": len(claims), "source_count": len(sources)}


def build_daily_brief_contract(
    *,
    market: dict[str, Any] | None = None,
    war_map: dict[str, Any] | None = None,
    news: dict[str, Any] | None = None,
    provider_rows: Iterable[dict[str, Any]] | None = None,
    watchlists: Iterable[dict[str, Any]] | None = None,
    period: str = "morning",
    runtime_mode: str = "cache",
    generated_at: str | datetime | None = None,
    previous_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_period = _text(period, limit=20).lower()
    if normalized_period not in PERIODS:
        raise ValueError("Invalid daily brief period.")
    mode = _text(runtime_mode, limit=40).lower()
    if mode not in RUNTIME_MODES:
        raise ValueError("Invalid daily brief runtime mode.")
    generated = generated_at if isinstance(generated_at, datetime) else _parse_time(generated_at)
    generated = _iso(generated or _utc_now())
    market_data = market.get("data") if isinstance((market or {}).get("data"), dict) else (market or {})
    map_data = war_map.get("data") if isinstance((war_map or {}).get("data"), dict) else (war_map or {})
    news_data = news.get("data") if isinstance((news or {}).get("data"), dict) else (news or {})
    register: dict[str, dict[str, Any]] = {}
    claims = [
        *_market_claims(_records(market_data.get("market_tape")), register),
        *_event_claims(_records(map_data.get("markers")), register),
        *_news_claims(_records(news_data.get("normalized_news")) or _records(news_data.get("event_rows")), register),
        *_provider_gap_claims(list(provider_rows or map_data.get("provider_health") or []), register),
        *_watchlist_claims(list(watchlists or []), register),
    ]
    claims = sorted(claims, key=lambda row: (row["section_id"], row["claim_id"]))
    chart_panels = _chart_panels(market_data, claims, register)
    sources = sorted(register.values(), key=lambda row: row["source_id"])
    research_perspectives = _research_perspectives(claims)
    sections = [
        _section("cross_asset", "Cross-asset pulse", claims),
        _section("global_risk", "Global risk", claims),
        _section("news_flow", "News flow", claims),
        _section("watchlist", "Watchlist context", claims),
        _section("data_quality", "Source coverage and gaps", claims),
    ]
    public_claim_ids = [row["claim_id"] for row in claims if row["privacy_scope"] == "public" and row["claim_kind"] != "gap"]
    gap_count = sum(row["claim_kind"] == "gap" for row in claims)
    source_status = _overall_status(sources)
    observed = sorted(filter(None, (_parse_time(row.get("observed_at")) for row in sources)))
    linked_symbols = sorted({item for row in claims for item in row["linked_symbols"]})
    linked_regions = sorted({item for row in claims for item in row["linked_regions"]})
    brief = {
        "daily_brief_version": DAILY_BRIEF_VERSION,
        "period": normalized_period,
        "runtime_mode": mode,
        "generated_at": generated,
        "observation_window": {
            "started_at": _iso(observed[0]) if observed else None,
            "ended_at": _iso(observed[-1]) if observed else None,
        },
        "privacy_scope": "local-private-composition" if any(row["privacy_scope"] == "local-private" for row in claims) else "public-composition",
        "historical_truth": "current-composition",
        "headline": {
            "text": f"{len(public_claim_ids)} public observations and {gap_count} explicit data gaps are ready for review.",
            "claim_ids": public_claim_ids[:6] + [row["claim_id"] for row in claims if row["claim_kind"] == "gap"][:3],
        },
        "claims": claims,
        "sections": sections,
        "chart_panels": chart_panels,
        "research_perspectives": research_perspectives,
        "source_register": sources,
        "coverage": {
            "source_status": source_status,
            "source_count": len(sources),
            "public_source_count": sum(row["privacy_scope"] == "public" for row in sources),
            "private_source_count": sum(row["privacy_scope"] == "local-private" for row in sources),
            "claim_count": len(claims),
            "chart_panel_count": len(chart_panels),
            "research_perspective_count": len(research_perspectives),
            "gap_count": gap_count,
            "status_counts": {status: sum(row["source_status"] == status for row in sources) for status in sorted({row["source_status"] for row in sources})},
        },
        "linked_symbols": linked_symbols,
        "linked_regions": linked_regions,
        "comparison": None,
        "review": {"status": "unread", "brief_id": None, "reviewed_at": None, "memory_link_available": True},
        "ai": {
            "default_mode": "deterministic-rule-based",
            "external_ai_enabled": False,
            "optional_provider": "gemini",
            "public_sanitized_evidence_only": True,
            "google_search_grounding": "explicit-opt-in-only",
        },
        "caveat": "Observations and calculations are research context only; temporal co-occurrence does not establish causality.",
        "not_financial_advice": True,
    }
    brief["comparison"] = diff_daily_briefs(previous_brief, brief) if previous_brief else None
    brief["validation"] = validate_daily_brief(brief)
    return brief


def _claim_map(brief: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {_text(row.get("claim_id")): row for row in _records(brief.get("claims")) if _text(row.get("claim_id"))}


def diff_daily_briefs(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = _claim_map(before)
    right = _claim_map(after)
    added = [{"claim_id": key, "after": right[key]} for key in sorted(right.keys() - left.keys())]
    removed = [{"claim_id": key, "before": left[key]} for key in sorted(left.keys() - right.keys())]
    changed: list[dict[str, Any]] = []
    refreshed: list[dict[str, Any]] = []
    unchanged = 0
    for key in sorted(left.keys() & right.keys()):
        if left[key] == right[key]:
            unchanged += 1
            continue
        differing = {field for field in set(left[key]) | set(right[key]) if left[key].get(field) != right[key].get(field)}
        material = sorted(differing - {"fetched_at"})
        if material:
            changed.append({"claim_id": key, "changed_fields": material, "before": left[key], "after": right[key]})
        else:
            refreshed.append({"claim_id": key, "before_fetched_at": left[key].get("fetched_at"), "after_fetched_at": right[key].get("fetched_at")})
            unchanged += 1
    summary = {"added": len(added), "removed": len(removed), "changed": len(changed), "unchanged": unchanged, "refreshed": len(refreshed)}
    return {
        "before_brief_id": before.get("brief_id") or before.get("capture_id"),
        "after_brief_id": after.get("brief_id") or after.get("capture_id"),
        "added": added, "removed": removed, "changed": changed, "refreshed": refreshed,
        "summary": summary,
        "source_preserved": True,
        "caveat": "Changes compare captured normalized claims only; temporal co-occurrence does not establish causality or real-world resolution.",
    }


def _semantic_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _semantic_value(item) for key, item in sorted(value.items()) if key not in VOLATILE_FIELDS and key not in {"comparison", "review", "validation"}}
    if isinstance(value, list):
        return [_semantic_value(item) for item in value]
    return value


def _content_hash(brief: dict[str, Any]) -> str:
    encoded = json.dumps(_semantic_value(brief), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def normalize_brief_id(value: Any, *, allow_empty: bool = False) -> str:
    text = _text(value, limit=80).lower()
    if allow_empty and not text:
        return ""
    if not BRIEF_ID_PATTERN.fullmatch(text):
        raise ValueError("Invalid daily brief id.")
    return text


def capture_daily_brief(
    brief: dict[str, Any], *, retention_days: int = 90, captured_at: str | datetime | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    validation = validate_daily_brief(brief)
    if not validation["valid"]:
        raise ValueError("Daily brief failed claim/source validation.")
    days = int(retention_days)
    if days < 1 or days > 3650:
        raise ValueError("retention_days must be between 1 and 3650.")
    captured = captured_at if isinstance(captured_at, datetime) else _parse_time(captured_at)
    captured = (captured or _utc_now()).astimezone(timezone.utc).replace(microsecond=0)
    digest = _content_hash(brief)
    brief_id = f"brief_{digest[:20]}"
    period = _text(brief.get("period"), limit=20).lower()
    if period not in PERIODS:
        raise ValueError("Invalid daily brief period.")
    with get_connection(db_path) as conn:
        existing = conn.execute("SELECT brief_id FROM daily_brief_captures WHERE content_hash = ?", (digest,)).fetchone()
        if existing:
            row = get_daily_brief_capture(str(existing[0]), db_path=db_path, include_payload=False)
            return {**row, "created": False, "deduplicated": True}
        previous_row = conn.execute("SELECT brief_id FROM daily_brief_captures WHERE period = ? ORDER BY captured_at DESC LIMIT 1", (period,)).fetchone()
        previous = get_daily_brief_capture(str(previous_row[0]), db_path=db_path) if previous_row else None
        comparison = diff_daily_briefs(previous, brief) if previous else None
        window = brief.get("observation_window") if isinstance(brief.get("observation_window"), dict) else {}
        claims = _records(brief.get("claims"))
        sections = _records(brief.get("sections"))
        sources = _records(brief.get("source_register"))
        coverage = dict(brief.get("coverage") or {})
        conn.execute(
            """
            INSERT INTO daily_brief_captures (
                brief_id, capture_version, content_hash, period, generated_at, captured_at,
                observation_started_at, observation_ended_at, runtime_mode, source_status,
                retention_days, retention_until, review_status, claim_count, section_count, gap_count,
                headline_json, claims_json, sections_json, source_register_json, coverage_json,
                comparison_json, linked_symbols_json, linked_regions_json, caveat, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brief_id, CAPTURE_VERSION, digest, period, _text(brief.get("generated_at"), limit=80), _iso(captured),
                window.get("started_at"), window.get("ended_at"), _text(brief.get("runtime_mode"), limit=40),
                _text(coverage.get("source_status"), limit=80, fallback="unknown"), days, _iso(captured + timedelta(days=days)),
                "unread", len(claims), len(sections), int(coverage.get("gap_count") or 0), _json(brief.get("headline") or {}),
                _json(claims), _json(sections), _json(sources), _json(coverage), _json(comparison or {}),
                _json(list(brief.get("linked_symbols") or [])), _json(list(brief.get("linked_regions") or [])),
                _text(brief.get("caveat")), _json({"local_private": True, "not_financial_advice": True}),
            ),
        )
        conn.commit()
    row = get_daily_brief_capture(brief_id, db_path=db_path, include_payload=False)
    return {**row, "created": True, "deduplicated": False}


def _capture_from_row(row: Any, *, include_payload: bool, include_private: bool = False) -> dict[str, Any]:
    data = dict(row)
    output = {key: data.get(key) for key in (
        "brief_id", "capture_version", "content_hash", "period", "generated_at", "captured_at",
        "observation_started_at", "observation_ended_at", "runtime_mode", "source_status", "retention_days",
        "retention_until", "review_status", "reviewed_at", "claim_count", "section_count", "gap_count", "caveat",
    )}
    output.update({
        "privacy_scope": "local-private", "historical_truth": "project-captured-brief",
        "headline": _loads(data.get("headline_json"), {}),
        "coverage": _loads(data.get("coverage_json"), {}),
        "comparison": _loads(data.get("comparison_json"), {}) or None,
        "linked_symbols": _loads(data.get("linked_symbols_json"), []),
        "linked_regions": _loads(data.get("linked_regions_json"), []),
    })
    if include_payload:
        output["claims"] = _loads(data.get("claims_json"), [])
        output["sections"] = _loads(data.get("sections_json"), [])
        output["source_register"] = _loads(data.get("source_register_json"), [])
        output["daily_brief_version"] = DAILY_BRIEF_VERSION
        output["not_financial_advice"] = True
    if include_private:
        output["review_notes"] = _text(data.get("review_notes"), limit=800)
    return output


def get_daily_brief_capture(brief_id: str, *, db_path: str | Path | None = None, include_payload: bool = True, include_private: bool = False) -> dict[str, Any]:
    safe_id = normalize_brief_id(brief_id)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM daily_brief_captures WHERE brief_id = ?", (safe_id,)).fetchone()
    if not row:
        raise KeyError("Daily brief capture not found.")
    return _capture_from_row(row, include_payload=include_payload, include_private=include_private)


def list_daily_brief_captures(*, period: str | None = None, limit: int = 120, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    bounded = max(1, min(int(limit), 365))
    params: list[Any] = []
    query = "SELECT * FROM daily_brief_captures"
    if period:
        normalized = _text(period, limit=20).lower()
        if normalized not in PERIODS:
            raise ValueError("Invalid daily brief period.")
        query += " WHERE period = ?"
        params.append(normalized)
    query += " ORDER BY captured_at DESC, brief_id DESC LIMIT ?"
    params.append(bounded)
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_capture_from_row(row, include_payload=False) for row in rows]


def update_daily_brief_review(
    brief_id: str, *, status: str, review_notes: str = "", db_path: str | Path | None = None,
) -> dict[str, Any]:
    safe_id = normalize_brief_id(brief_id)
    normalized = _text(status, limit=20).lower()
    if normalized not in REVIEW_STATUSES:
        raise ValueError("Invalid daily brief review status.")
    reviewed_at = _iso(_utc_now()) if normalized == "reviewed" else None
    private_notes = _text(review_notes, limit=800)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE daily_brief_captures SET review_status = ?, reviewed_at = ?, review_notes = ? WHERE brief_id = ?",
            (normalized, reviewed_at, private_notes, safe_id),
        )
        conn.commit()
    if not cursor.rowcount:
        raise KeyError("Daily brief capture not found.")
    return get_daily_brief_capture(safe_id, db_path=db_path, include_payload=False)


def prune_expired_daily_briefs(*, as_of: str | datetime | None = None, db_path: str | Path | None = None) -> int:
    current = as_of if isinstance(as_of, datetime) else _parse_time(as_of)
    current = (current or _utc_now()).astimezone(timezone.utc).replace(microsecond=0)
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM daily_brief_captures WHERE retention_until < ?", (_iso(current),))
        conn.commit()
        return int(cursor.rowcount)


def build_daily_brief_history_contract(
    *, brief_id: str | None = None, compare_to: str | None = None, period: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    captures = list_daily_brief_captures(period=period, db_path=db_path)
    if not captures:
        return {
            "daily_brief_history_version": "daily_brief_history.v1", "privacy_scope": "local-private",
            "historical_truth": "empty-local-store", "captures": [], "active_capture": None,
            "comparison_capture": None, "comparison": None,
            "readiness": {"capture_available": True, "review_available": False, "compare_available": False, "capture_count": 0},
            "caveat": "No local daily brief has been captured; uncaptured history is not backfilled.",
        }
    active_id = normalize_brief_id(brief_id, allow_empty=True) or str(captures[0]["brief_id"])
    compare_id = normalize_brief_id(compare_to, allow_empty=True)
    active = get_daily_brief_capture(active_id, db_path=db_path)
    comparison_capture = get_daily_brief_capture(compare_id, db_path=db_path) if compare_id else None
    comparison = diff_daily_briefs(comparison_capture, active) if comparison_capture else active.get("comparison")
    return {
        "daily_brief_history_version": "daily_brief_history.v1", "privacy_scope": "local-private",
        "historical_truth": "project-captured-briefs-only", "captures": captures, "active_capture": active,
        "comparison_capture": comparison_capture, "comparison": comparison,
        "readiness": {"capture_available": True, "review_available": True, "compare_available": len(captures) >= 2, "capture_count": len(captures)},
        "caveat": "History contains only project-captured briefs; removed claims do not prove real-world resolution.",
    }


def build_ai_safe_public_brief(brief: dict[str, Any]) -> dict[str, Any]:
    sources = [row for row in _records(brief.get("source_register")) if row.get("privacy_scope") == "public"]
    source_ids = {row["source_id"] for row in sources}
    claims = [
        {key: value for key, value in row.items() if key not in PRIVATE_KEYS}
        for row in _records(brief.get("claims"))
        if row.get("privacy_scope") == "public" and set(row.get("source_ids") or []) <= source_ids
    ]
    return {
        "daily_brief_version": brief.get("daily_brief_version"), "period": brief.get("period"),
        "privacy_scope": "public-sanitized-ai-input", "claims": claims, "source_register": sources,
        "instructions": "Draft only from the supplied claim IDs. Do not add advice, causality, targets, or unsupported facts.",
    }


def validate_ai_brief_draft(draft: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    known = set(_claim_map(brief))
    issues: list[str] = []
    paragraphs = _records(draft.get("paragraphs"))
    if not paragraphs:
        issues.append("AI draft has no structured paragraphs.")
    for index, paragraph in enumerate(paragraphs):
        text = _text(paragraph.get("text"))
        refs = {_text(item) for item in list(paragraph.get("claim_ids") or []) if _text(item)}
        if text and not refs:
            issues.append(f"Paragraph {index} has no claim IDs.")
        if not refs <= known:
            issues.append(f"Paragraph {index} references unknown claim IDs.")
        for phrase in [*find_forbidden_report_phrases(text), *[token for token in ("buy now", "sell now", "target price") if token in text.lower()]]:
            issues.append(f"Paragraph {index} contains unsupported language: {phrase}.")
    return {"valid": not issues, "issues": sorted(set(issues)), "paragraph_count": len(paragraphs)}


def _demo_inputs(*, changed: bool) -> dict[str, Any]:
    fetched = "2026-06-23T00:30:00+00:00" if changed else "2026-06-22T00:30:00+00:00"
    base = {"provider": "fictional-demo", "source": "Phase 5Q fictional fixture", "source_url": "https://example.test/phase-5q", "fetched_at": fetched, "freshness": "fixture", "source_status": "fixture", "confidence": 0.35, "caveat": "Fictional deterministic fixture.", "data_gap": "Not live market evidence."}
    market = {"market_tape": [{**base, "symbol": "SPY", "label": "Fictional US market proxy", "last_price": 550.0, "daily_return_pct": 0.8 if changed else 0.2, "one_month_return_pct": 1.4}]}
    markers = [{**base, "marker_id": "demo-global-event-one", "title": "Fictional logistics watch", "region": "Demo Strait", "severity": "elevated" if changed else "watch", "severity_score": 70 if changed else 40, "timestamp": fetched, "related_asset_node_ids": ["commodity:brent"]}]
    news = {"normalized_news": [{**base, "title": "Fictional policy briefing published", "published_at": fetched, "region": "Demo Europe", "related_assets": ["EURUSD"]}]}
    providers = [{**base, "provider": "fictional-flight-provider", "status": "unavailable", "source_status": "unavailable", "data_gap": "Fictional flight coverage is unavailable."}]
    return {"market": market, "war_map": {"markers": markers}, "news": news, "provider_rows": providers, "watchlists": []}


def build_demo_daily_brief_contract() -> dict[str, Any]:
    before = build_daily_brief_contract(**_demo_inputs(changed=False), period="morning", runtime_mode="fixture", generated_at="2026-06-22T00:35:00+00:00")
    active = build_daily_brief_contract(**_demo_inputs(changed=True), period="morning", runtime_mode="fixture", generated_at="2026-06-23T00:35:00+00:00", previous_brief=before)
    active["privacy_scope"] = "deterministic-public-fixture"
    active["historical_truth"] = "fictional-demo"
    active["demo_prior_brief"] = {"generated_at": before["generated_at"], "headline": before["headline"], "claims": before["claims"], "source_register": before["source_register"]}
    active["validation"] = validate_daily_brief(active)
    return active


def build_current_daily_brief_contract(
    *, period: str = "morning", include_runtime: bool = False, db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compose current first-party contracts without introducing a Streamlit boundary."""
    from .market_intelligence import build_market_intelligence_contract
    from .news_intelligence import build_worldmonitor_style_news_dashboard
    from .research_memory import build_research_memory_contract
    from .war_room import build_war_room_state
    from .war_room_map import build_war_room_map_contract

    market = build_market_intelligence_contract(include_runtime=include_runtime)
    state = build_war_room_state(include_default_runtime=include_runtime)
    providers = _records(state.get("provider_health_ledger"))
    try:
        from .live_feeds import fetch_aisstream_optional_status, fetch_opensky_optional_status

        optional_statuses = [fetch_opensky_optional_status(), fetch_aisstream_optional_status()]
        existing_provider_names = {_text(row.get("provider"), limit=120).lower() for row in providers}
        for row in optional_statuses:
            provider_name = _text(row.get("provider"), limit=120).lower()
            if provider_name and provider_name not in existing_provider_names:
                if _status(row) == "configured":
                    row = {
                        **row,
                        "status": "configured-unverified",
                        "source_status": "configured-unverified",
                        "availability": "unavailable",
                        "data_gap": _text(
                            row.get("data_gap") or row.get("warning") or row.get("caveat"),
                            fallback="Optional credentials are configured, but no successful live row fetch is attached to this brief.",
                        ),
                    }
                providers.append(row)
                existing_provider_names.add(provider_name)
    except Exception:
        pass
    war_map = build_war_room_map_contract(state=state, provider_rows=providers)
    runtime = state.get("runtime_feeds") if isinstance(state.get("runtime_feeds"), dict) else {}
    news = build_worldmonitor_style_news_dashboard(
        items=runtime.get("news") or [],
        statuses=runtime.get("source_statuses") or [],
    )
    try:
        memory = build_research_memory_contract(mode="local", collection_id="local-research", db_path=db_path)
        watchlists = _records(memory.get("watchlists"))
    except Exception:
        watchlists = []
    prior_rows = list_daily_brief_captures(period=period, limit=1, db_path=db_path)
    previous = get_daily_brief_capture(prior_rows[0]["brief_id"], db_path=db_path) if prior_rows else None
    return build_daily_brief_contract(
        market=market,
        war_map=war_map,
        news=news,
        provider_rows=providers,
        watchlists=watchlists,
        period=period,
        runtime_mode="live-if-available" if include_runtime else "cache",
        previous_brief=previous,
    )
