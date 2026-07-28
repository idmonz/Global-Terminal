from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode, urlsplit, urlunsplit

from .identity_tenancy import _require_authenticated, public_account_payload
from .research_workspace_db import execute_query, get_connection, new_id


ATTENTION_DESK_VERSION = "attention_desk.v1"
MAX_ATTENTION_ITEMS = 100
MAX_DIGEST_ITEMS = 7
MAX_AUDIT_ROWS = 100
MAX_SNOOZE_DAYS = 30

_SEVERITY_SCORE = {"info": 10, "material": 30, "high": 50, "critical": 70}
_SEVERITY_ALIASES = {
    "context": "info",
    "low": "info",
    "watch": "material",
    "medium": "material",
    "elevated": "high",
    "warning": "high",
    "danger": "critical",
    "severe": "critical",
}
_KIND_ALIASES = {
    "price": "market-change",
    "performance": "market-change",
    "fundamental": "market-change",
    "market": "market-change",
    "event": "new-evidence",
    "news": "new-evidence",
    "catalyst": "new-evidence",
    "source-status": "source-degradation",
    "provider-health": "source-degradation",
    "stale": "stale-evidence",
    "resolved": "resolved",
    "fetch-refresh": "fetch-refresh",
}
_VALID_KINDS = {
    "market-change",
    "new-evidence",
    "source-degradation",
    "stale-evidence",
    "resolved",
    "fetch-refresh",
}
_DEGRADED_STATUSES = {
    "error",
    "failed",
    "forbidden/subscription-blocked",
    "missing-key",
    "partial",
    "rate-limited",
    "stale",
    "unavailable",
}
_CLIENT_IDENTITY_FIELDS = {"tenant_id", "user_id", "owner_user_id", "role", "plan"}
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_PHRASES = (
    "buy now",
    "sell now",
    "place order",
    "target price",
    "take profit",
    "stop loss",
    "enter the trade",
    "exit the trade",
    "overweight recommendation",
    "underweight recommendation",
)


class AttentionConflict(RuntimeError):
    def __init__(self, current_version: int):
        super().__init__("Attention state version conflict.")
        self.current_version = int(current_version)


def _iso(value: datetime | str | None = None) -> str | None:
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        current = value
    else:
        try:
            current = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _dt(value: Any) -> datetime | None:
    normalized = _iso(value)
    return datetime.fromisoformat(normalized) if normalized else None


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0)


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(value: Any, default: str = "") -> str:
    return str(value if value not in {None, ""} else default).strip()


def _rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(row) for row in value if isinstance(row, dict)]
    if isinstance(value, tuple):
        return [dict(row) for row in value if isinstance(row, dict)]
    return []


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _unwrap(value: Any) -> Any:
    if isinstance(value, dict) and "data" in value and "payload_type" in value:
        return value.get("data")
    return value


def _canonical_url(value: Any) -> str:
    raw = _text(value)
    if not raw.startswith(("https://", "http://")):
        return ""
    try:
        split = urlsplit(raw)
        host = split.netloc.lower()
        path = split.path.rstrip("/") or "/"
        return urlunsplit((split.scheme.lower(), host, path, split.query, ""))
    except ValueError:
        return ""


def _severity(value: Any, *, default: str = "material") -> str:
    normalized = _text(value, default).lower().replace("_", "-")
    normalized = _SEVERITY_ALIASES.get(normalized, normalized)
    return normalized if normalized in _SEVERITY_SCORE else default


def _kind(value: Any, *, default: str = "new-evidence") -> str:
    normalized = _text(value, default).lower().replace("_", "-")
    normalized = _KIND_ALIASES.get(normalized, normalized)
    return normalized if normalized in _VALID_KINDS else default


def _status(value: Any) -> str:
    return _text(value, "unavailable").lower()


def _subject(row: dict[str, Any], *, fallback_type: str) -> dict[str, str]:
    symbol = _text(row.get("symbol") or row.get("ticker")).upper()
    region = _text(row.get("region") or row.get("location") or row.get("country"))
    provider = _text(row.get("provider") or row.get("source"))
    subject_id = symbol or region or provider or _text(row.get("event_id") or row.get("claim_id") or row.get("marker_id"))
    label = _text(row.get("display_name") or row.get("name") or row.get("label")) or symbol or region or provider or "Source evidence"
    subject_type = "asset" if symbol else ("region" if region else fallback_type)
    return {
        "type": subject_type,
        "id": subject_id[:120],
        "label": label[:160],
        "symbol": symbol[:32],
        "region": region[:120],
    }


def _origin_id(row: dict[str, Any], origin: str) -> str:
    for key in ("change_id", "event_id", "claim_id", "marker_id", "resource_id", "id"):
        if row.get(key):
            return f"{origin}:{_text(row.get(key))[:160]}"
    url = _canonical_url(row.get("source_url") or row.get("url"))
    if url:
        return f"{origin}:url:{url}"
    return f"{origin}:hash:{_hash([row.get('title'), row.get('statement'), row.get('symbol'), row.get('region')])[:24]}"


def _evidence_identity(row: dict[str, Any], origin: str) -> str:
    url = _canonical_url(row.get("source_url") or row.get("url"))
    if url:
        return f"url:{url}"
    for key in ("event_id", "change_id", "claim_id", "marker_id", "resource_id", "id"):
        if row.get(key):
            return f"{origin}:{_text(row.get(key))[:160]}"
    return f"{origin}:semantic:{_hash([row.get('title'), row.get('statement'), row.get('symbol'), row.get('region'), row.get('observed_at'), row.get('published_at')])}"


def _origin_state(mode: str = "cache") -> str:
    return urlencode({"mode": mode, "review": "needs-review"})


def _return_url(mode: str = "cache") -> str:
    return "/?" + urlencode({"view": "attention-desk", "mode": mode, "review": "needs-review"})


def _drilldowns(origin: str, row: dict[str, Any], *, mode: str = "cache") -> dict[str, str]:
    state = _origin_state(mode)
    common = {"originView": "attention-desk", "originState": state}
    subject = _subject(row, fallback_type="evidence")
    symbol = subject["symbol"]
    region = subject["region"]
    origin_id = _origin_id(row, origin)
    output: dict[str, str] = {}
    if symbol:
        output["analyst"] = "/?" + urlencode(
            {
                "view": "analyst-workspace",
                "symbol": symbol,
                "assetClass": _text(row.get("asset_class"), "equity"),
                "mode": mode,
                "panel": "catalysts" if origin == "catalyst" else "overview",
                **common,
            }
        )
    if origin in {"news", "daily-brief", "war-map"} or row.get("source_url"):
        output["news"] = "/?" + urlencode(
            {"view": "news", "mode": mode, "region": region, "topic": symbol or region, "originId": origin_id, **common}
        )
    if origin == "daily-brief":
        output["brief"] = "/?" + urlencode(
            {"view": "daily-brief", "mode": mode, "period": "morning", "section": _text(row.get("section_id"), "overview"), "originId": origin_id, **common}
        )
    if origin == "war-map" or region:
        output["map"] = "/?" + urlencode(
            {"view": "war-room-map", "mode": mode, "region": region, "selected": _text(row.get("marker_id")), "originId": origin_id, **common}
        )
    if origin == "watchlist-change":
        output["watchlist"] = "/?" + urlencode(
            {"view": "watchlist-desk", "mode": "local", "list": _text(row.get("list_id"), "primary"), "change": _text(row.get("change_id")), **common}
        )
    return {key: value for key, value in output.items() if value}


def _candidate(
    row: dict[str, Any],
    *,
    origin: str,
    change_kind: str,
    title: str,
    summary: str,
    severity: str | None = None,
    material: bool = True,
    mode: str = "cache",
) -> dict[str, Any]:
    source_url = _canonical_url(row.get("source_url") or row.get("url"))
    observed_at = _iso(row.get("observed_at") or row.get("published_at") or row.get("event_date") or row.get("ex_dividend_date"))
    retrieved_at = _iso(row.get("retrieved_at") or row.get("fetched_at") or row.get("checked_at") or row.get("generated_at"))
    provider = _text(row.get("provider") or row.get("source"), "unknown")[:120]
    source_status = _status(row.get("source_status") or row.get("freshness") or row.get("status"))
    normalized_kind = _kind(change_kind)
    normalized_severity = _severity(severity or row.get("severity"), default="material" if material else "info")
    identity = _evidence_identity(row, origin)
    subject = _subject(row, fallback_type="provider" if origin == "provider-health" else "evidence")
    origin_id = _origin_id(row, origin)
    confidence = row.get("confidence")
    try:
        confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None else None
    except (TypeError, ValueError):
        confidence = None
    item = {
        "fingerprint": _hash(f"attention:{identity}"),
        "content_fingerprint": "",
        "evidence_identity": identity,
        "origin_kind": origin,
        "origin_id": origin_id,
        "origins": [origin],
        "subject": subject,
        "change_kind": normalized_kind,
        "severity": normalized_severity,
        "material": bool(material and normalized_kind != "fetch-refresh"),
        "title": _text(title, "Source-linked evidence changed")[:220],
        "summary": _text(summary, "Review the exact source and observation clock.")[:1_200],
        "why_it_matters": "",
        "observed_at": observed_at,
        "retrieved_at": retrieved_at,
        "provider": provider,
        "source_url": source_url,
        "source_status": source_status,
        "confidence": confidence,
        "caveat": _text(row.get("caveat"))[:1_000],
        "data_gap": _text(row.get("data_gap") or row.get("warning") or row.get("error"))[:1_000],
        "coordinate_method": _text(row.get("coordinate_method"))[:120],
        "review_state": "new",
        "review_version": 0,
        "snoozed_until": None,
        "snooze_expired": False,
        "drilldowns": _drilldowns(origin, row, mode=mode),
        "return_url": _return_url(mode),
        "source_register": [
            {
                "provider": provider,
                "source_url": source_url,
                "source_status": source_status,
                "observed_at": observed_at,
                "retrieved_at": retrieved_at,
                "confidence": confidence,
                "caveat": _text(row.get("caveat"))[:500],
                "data_gap": _text(row.get("data_gap") or row.get("warning") or row.get("error"))[:500],
                "origins": [origin],
            }
        ],
        "rank": {"score": 0, "factors": []},
        "provider_call_count": 0,
        "not_financial_advice": True,
    }
    item["content_fingerprint"] = _hash(
        {
            "subject": subject,
            "change_kind": normalized_kind,
            "severity": normalized_severity,
            "title": item["title"],
            "summary": item["summary"],
            "source_status": source_status,
        }
    )
    return item


def _watchlist_candidates(rows: Iterable[dict[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        raw_type = _text(row.get("change_type") or row.get("type"), "market")
        kind = _kind(raw_type, default="market-change")
        if _status(row.get("source_status")) in _DEGRADED_STATUSES or raw_type == "source-status":
            kind = "source-degradation"
        output.append(
            _candidate(
                row,
                origin="watchlist-change",
                change_kind=kind,
                title=_text(row.get("title"), f"{_text(row.get('symbol'), 'Saved symbol')} changed"),
                summary=_text(row.get("summary") or row.get("description"), "A completed saved observation changed."),
                mode=mode,
            )
        )
    return output


def _catalyst_candidates(rows: Iterable[dict[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        event_type = _text(row.get("event_type"), "catalyst").replace("-", " ")
        symbol = _text(row.get("symbol"), "Asset")
        output.append(
            _candidate(
                row,
                origin="catalyst",
                change_kind="new-evidence",
                title=_text(row.get("title"), f"{symbol} {event_type} recorded"),
                summary=_text(row.get("summary"), "A source-linked catalyst record is available for exact review."),
                severity=_text(row.get("severity"), "material"),
                mode=mode,
            )
        )
    return output


def _news_candidates(rows: Iterable[dict[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    return [
        _candidate(
            row,
            origin="news",
            change_kind="new-evidence",
            title=_text(row.get("title") or row.get("headline"), "Source report recorded"),
            summary=_text(row.get("summary") or row.get("description"), "Open the exact report for source context."),
            severity=_text(row.get("severity"), "material"),
            mode=mode,
        )
        for row in rows
    ]


def _brief_candidates(brief: dict[str, Any], *, mode: str) -> list[dict[str, Any]]:
    comparison = _record(brief.get("comparison"))
    output: list[dict[str, Any]] = []
    for change in _rows(comparison.get("changed")):
        after = _record(change.get("after"))
        if not after:
            continue
        row = {**after, "claim_id": change.get("claim_id") or after.get("claim_id")}
        output.append(
            _candidate(
                row,
                origin="daily-brief",
                change_kind="new-evidence",
                title=_text(after.get("statement"), "Daily Brief claim changed"),
                summary="Changed fields: " + ", ".join(str(field) for field in change.get("changed_fields") or []),
                severity=_text(after.get("severity"), "material"),
                mode=mode,
            )
        )
    for added in _rows(comparison.get("added")):
        output.append(
            _candidate(
                added,
                origin="daily-brief",
                change_kind="new-evidence",
                title=_text(added.get("statement"), "Daily Brief claim added"),
                summary="A normalized source-linked claim was added to the captured comparison.",
                severity=_text(added.get("severity"), "material"),
                mode=mode,
            )
        )
    for removed in _rows(comparison.get("removed")):
        output.append(
            _candidate(
                removed,
                origin="daily-brief",
                change_kind="resolved",
                title=_text(removed.get("statement"), "Daily Brief claim no longer appears"),
                summary="The claim is absent from the newer normalized capture; this does not prove real-world resolution.",
                severity="material",
                mode=mode,
            )
        )
    for refreshed in _rows(comparison.get("refreshed")):
        row = {
            **refreshed,
            "fetched_at": refreshed.get("after_fetched_at"),
            "source_status": "cached",
            "provider": "daily-brief",
        }
        output.append(
            _candidate(
                row,
                origin="daily-brief",
                change_kind="fetch-refresh",
                title="Daily Brief source retrieval clock refreshed",
                summary="Only the retrieval clock changed; no material claim change is promoted.",
                severity="info",
                material=False,
                mode=mode,
            )
        )
    return output


def _provider_candidates(rows: Iterable[dict[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        status = _status(row.get("source_status") or row.get("status"))
        if status not in _DEGRADED_STATUSES:
            continue
        severity = "high" if status in {"failed", "error", "forbidden/subscription-blocked"} else "material"
        output.append(
            _candidate(
                row,
                origin="provider-health",
                change_kind="source-degradation" if status != "stale" else "stale-evidence",
                title=f"{_text(row.get('provider'), 'Provider')} source state: {status}",
                summary=_text(row.get("warning") or row.get("error") or row.get("recommended_action"), "Source delivery is degraded; last-known evidence is retained with its clock."),
                severity=severity,
                mode=mode,
            )
        )
    return output


def _war_map_candidates(rows: Iterable[dict[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    return [
        _candidate(
            row,
            origin="war-map",
            change_kind="new-evidence",
            title=_text(row.get("title"), "Map event evidence recorded"),
            summary=_text(row.get("summary"), "The map links source evidence to a region and transmission context."),
            severity=_text(row.get("severity"), "material"),
            mode=mode,
        )
        for row in rows
    ]


def _merge_text(left: Any, right: Any, *, limit: int) -> str:
    values = []
    for value in (_text(left), _text(right)):
        if value and value not in values:
            values.append(value)
    return "; ".join(values)[:limit]


def _merge_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    origin_priority = {"watchlist-change": 60, "provider-health": 55, "daily-brief": 50, "catalyst": 45, "news": 40, "war-map": 35}
    for candidate in candidates:
        identity = candidate["evidence_identity"]
        current = grouped.get(identity)
        if current is None:
            grouped[identity] = candidate
            continue
        if (
            _SEVERITY_SCORE[candidate["severity"]],
            origin_priority.get(candidate["origin_kind"], 0),
        ) > (
            _SEVERITY_SCORE[current["severity"]],
            origin_priority.get(current["origin_kind"], 0),
        ):
            primary = deepcopy(candidate)
            secondary = current
        else:
            primary = current
            secondary = candidate
        primary["origins"] = sorted(set(current["origins"]) | set(candidate["origins"]))
        primary["material"] = bool(current["material"] or candidate["material"])
        primary["severity"] = max((current["severity"], candidate["severity"]), key=lambda value: _SEVERITY_SCORE[value])
        primary_subject = _record(primary.get("subject"))
        secondary_subject = _record(secondary.get("subject"))
        merged_subject = {
            key: _text(primary_subject.get(key)) or _text(secondary_subject.get(key))
            for key in ("type", "id", "label", "symbol", "region")
        }
        if merged_subject["symbol"]:
            merged_subject["type"] = "asset"
            merged_subject["id"] = merged_subject["symbol"]
        elif merged_subject["region"]:
            merged_subject["type"] = "region"
            merged_subject["id"] = merged_subject["region"]
        primary["subject"] = merged_subject
        primary["observed_at"] = max(filter(None, (current.get("observed_at"), candidate.get("observed_at"))), default=None)
        primary["retrieved_at"] = max(filter(None, (current.get("retrieved_at"), candidate.get("retrieved_at"))), default=None)
        primary["caveat"] = _merge_text(current.get("caveat"), candidate.get("caveat"), limit=1_000)
        primary["data_gap"] = _merge_text(current.get("data_gap"), candidate.get("data_gap"), limit=1_000)
        confidence_values = [value for value in (current.get("confidence"), candidate.get("confidence")) if isinstance(value, (int, float))]
        primary["confidence"] = min(confidence_values) if confidence_values else None
        primary["drilldowns"] = {**secondary.get("drilldowns", {}), **primary.get("drilldowns", {})}
        source_map: dict[tuple[str, str, str], dict[str, Any]] = {}
        for source in [*current.get("source_register", []), *candidate.get("source_register", [])]:
            key = (_text(source.get("provider")), _text(source.get("source_url")), _text(source.get("source_status")))
            if key in source_map:
                source_map[key]["origins"] = sorted(set(source_map[key].get("origins", [])) | set(source.get("origins", [])))
            else:
                source_map[key] = deepcopy(source)
        primary["source_register"] = sorted(source_map.values(), key=lambda row: (row["provider"], row["source_url"], row["source_status"]))
        primary["content_fingerprint"] = _hash(
            {
                "subject": primary["subject"],
                "change_kind": primary["change_kind"],
                "severity": primary["severity"],
                "title": primary["title"],
                "summary": primary["summary"],
                "sources": [(row["provider"], row["source_url"], row["source_status"]) for row in primary["source_register"]],
            }
        )
        grouped[identity] = primary
    return list(grouped.values())


def _reason(kind: str) -> str:
    if kind == "market-change":
        return "A completed saved market observation changed; open the exact comparison before revising research."
    if kind == "source-degradation":
        return "Evidence delivery degraded; last-known evidence remains visible with its observation and retrieval clocks."
    if kind == "stale-evidence":
        return "The saved evidence exceeded its freshness boundary and should be read as stale."
    if kind == "resolved":
        return "A prior normalized claim no longer appears; absence alone does not prove real-world resolution."
    if kind == "fetch-refresh":
        return "Only the retrieval clock changed, so this row is not promoted as a material change."
    return "New source-linked evidence is available for the named subject and exact origin."


def _rank(item: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    score = _SEVERITY_SCORE[item["severity"]]
    factors = [f"severity:{item['severity']}+{_SEVERITY_SCORE[item['severity']]}" ]
    if item["review_state"] == "new":
        score += 20
        factors.append("review:new+20")
    elif item["review_state"] == "reviewed":
        score += 5
        factors.append("review:reviewed+5")
    elif item["review_state"] == "acknowledged":
        score -= 20
        factors.append("review:acknowledged-20")
    if item["change_kind"] in {"source-degradation", "stale-evidence"}:
        score += 12
        factors.append("source-health+12")
    clock = _dt(item.get("observed_at") or item.get("retrieved_at"))
    if clock:
        age_hours = max(0.0, (now - clock).total_seconds() / 3600)
        recency = 10 if age_hours <= 6 else (6 if age_hours <= 24 else (2 if age_hours <= 72 else 0))
        score += recency
        factors.append(f"recency:{int(age_hours)}h+{recency}")
    if not item.get("source_url"):
        score -= 3
        factors.append("source-url-missing-3")
    return {"score": max(0, int(score)), "factors": factors}


def _default_policy() -> dict[str, Any]:
    return {
        "minimum_severity": "info",
        "included_change_kinds": sorted(_VALID_KINDS - {"fetch-refresh"}),
        "source_health_handling": "include",
        "version": 0,
        "updated_at": None,
    }


def validate_attention_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Attention policy must be an object.")
    if _CLIENT_IDENTITY_FIELDS.intersection(value):
        raise ValueError("Tenant and user identity are server-derived.")
    minimum = _severity(value.get("minimum_severity"), default="material")
    raw_kinds = value.get("included_change_kinds")
    if not isinstance(raw_kinds, list) or not raw_kinds:
        raise ValueError("included_change_kinds must be a non-empty list.")
    kinds = []
    for raw in raw_kinds[: len(_VALID_KINDS)]:
        normalized = _kind(raw)
        if normalized == "fetch-refresh":
            continue
        if normalized not in kinds:
            kinds.append(normalized)
    if not kinds:
        raise ValueError("Attention policy must include at least one material change kind.")
    handling = _text(value.get("source_health_handling"), "include").lower()
    if handling not in {"include", "deprioritize", "hide"}:
        raise ValueError("source_health_handling must be include, deprioritize, or hide.")
    version = value.get("version", 0)
    if not isinstance(version, int) or version < 0:
        raise ValueError("Attention policy version must be a non-negative integer.")
    return {
        "minimum_severity": minimum,
        "included_change_kinds": sorted(kinds),
        "source_health_handling": handling,
        "version": version,
        "updated_at": _iso(value.get("updated_at")),
    }


def _apply_review(item: dict[str, Any], state: dict[str, Any] | None, *, now: datetime) -> dict[str, Any]:
    output = dict(item)
    if not state:
        return output
    review_state = _text(state.get("review_state"), "new")
    snoozed_until = _dt(state.get("snoozed_until"))
    expired = review_state == "snoozed" and bool(snoozed_until and snoozed_until <= now)
    if expired:
        review_state = _text(state.get("prior_state"), "new")
    output.update(
        {
            "review_state": review_state,
            "review_version": int(state.get("version") or 0),
            "snoozed_until": _iso(state.get("snoozed_until")),
            "snooze_expired": expired,
            "reviewed_at": _iso(state.get("reviewed_at")),
            "acknowledged_at": _iso(state.get("acknowledged_at")),
        }
    )
    return output


def _apply_policy(items: list[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    minimum = _SEVERITY_SCORE[policy["minimum_severity"]]
    included = set(policy["included_change_kinds"])
    handling = policy["source_health_handling"]
    output = []
    for item in items:
        if not item["material"] or _SEVERITY_SCORE[item["severity"]] < minimum or item["change_kind"] not in included:
            continue
        if item["review_state"] == "snoozed":
            continue
        if handling == "hide" and item["change_kind"] in {"source-degradation", "stale-evidence"}:
            continue
        row = dict(item)
        if handling == "deprioritize" and row["change_kind"] in {"source-degradation", "stale-evidence"}:
            row["policy_rank_adjustment"] = -15
        output.append(row)
    return output


def _source_digest(items: list[dict[str, Any]]) -> dict[str, Any]:
    degraded = [item for item in items if item["change_kind"] in {"source-degradation", "stale-evidence"}]
    providers = sorted({_text(source.get("provider")) for item in items for source in item.get("source_register", []) if source.get("provider")})
    return {
        "headline": f"{len(items)} material attention rows across {len(providers)} named sources.",
        "items": [
            {
                "fingerprint": item["fingerprint"],
                "title": item["title"],
                "severity": item["severity"],
                "why_it_matters": item["why_it_matters"],
                "provider": item["provider"],
                "source_url": item["source_url"],
                "source_status": item["source_status"],
                "observed_at": item["observed_at"],
                "retrieved_at": item["retrieved_at"],
                "drilldowns": item["drilldowns"],
            }
            for item in items[:MAX_DIGEST_ITEMS]
        ],
        "source_count": len(providers),
        "degraded_source_count": len(degraded),
        "bounded": True,
        "max_items": MAX_DIGEST_ITEMS,
        "ai_used": False,
        "provider_call_count": 0,
        "caveat": "Deterministic source-linked digest; no unsupported narrative or recommendation is added.",
    }


def filter_and_rank_attention_items(
    items: Iterable[dict[str, Any]],
    *,
    policy: dict[str, Any] | None = None,
    review_states: dict[str, dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply local review state and policy without fetching or normalizing sources."""
    current = _now(now)
    normalized_policy = validate_attention_policy(policy) if policy else _default_policy()
    states = review_states or {}
    all_items: list[dict[str, Any]] = []
    for row in items:
        item = _apply_review(row, states.get(row["fingerprint"]), now=current)
        item["why_it_matters"] = _reason(item["change_kind"])
        item["rank"] = _rank(item, now=current)
        all_items.append(item)
    material_items = [item for item in all_items if item["material"]]
    visible = _apply_policy(material_items, normalized_policy)
    for item in visible:
        item["rank"] = _rank(item, now=current)
        if item.get("policy_rank_adjustment"):
            item["rank"]["score"] += int(item["policy_rank_adjustment"])
            item["rank"]["factors"].append(f"policy{int(item['policy_rank_adjustment']):+d}")
    visible.sort(key=lambda row: (-int(row["rank"]["score"]), _text(row.get("observed_at"), "9999"), row["fingerprint"]))
    all_items.sort(key=lambda row: (not row["material"], -int(row["rank"]["score"]), row["fingerprint"]))
    return all_items, visible


def build_attention_desk_contract(
    *,
    watchlist_changes: Iterable[dict[str, Any]] | None = None,
    catalysts: Iterable[dict[str, Any]] | None = None,
    news_rows: Iterable[dict[str, Any]] | None = None,
    daily_brief: dict[str, Any] | None = None,
    provider_health: Iterable[dict[str, Any]] | None = None,
    war_map_events: Iterable[dict[str, Any]] | None = None,
    review_states: dict[str, dict[str, Any]] | None = None,
    policy: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
    observation_run: dict[str, Any] | None = None,
    now: datetime | None = None,
    mode: str = "cache",
) -> dict[str, Any]:
    current = _now(now)
    normalized_policy = validate_attention_policy(policy) if policy else _default_policy()
    observation_context = _record(observation_run)
    observation_changes = _rows(observation_context.get("changes"))
    candidates = [
        *_watchlist_candidates(
            [*_rows(list(watchlist_changes or [])), *observation_changes],
            mode=mode,
        ),
        *_catalyst_candidates(_rows(list(catalysts or [])), mode=mode),
        *_news_candidates(_rows(list(news_rows or [])), mode=mode),
        *_brief_candidates(_record(_unwrap(daily_brief or {})), mode=mode),
        *_provider_candidates(_rows(list(provider_health or [])), mode=mode),
        *_war_map_candidates(_rows(list(war_map_events or [])), mode=mode),
    ]
    merged = _merge_candidates(candidates)[:MAX_ATTENTION_ITEMS]
    all_items, visible = filter_and_rank_attention_items(
        merged,
        policy=normalized_policy,
        review_states=review_states,
        now=current,
    )
    material_items = [item for item in all_items if item["material"]]
    checkpoint_data = {
        "reviewed_through_at": _iso((checkpoint or {}).get("reviewed_through_at")),
        "version": int((checkpoint or {}).get("version") or 0),
        "provider_clock_unchanged": True,
    }
    checkpoint_time = _dt(checkpoint_data["reviewed_through_at"])
    since = [
        item
        for item in material_items
        if checkpoint_time is None or (_dt(item.get("observed_at") or item.get("retrieved_at")) or datetime.min.replace(tzinfo=timezone.utc)) > checkpoint_time
    ]
    since_summary = {
        "new": sum(item["review_state"] == "new" for item in since),
        "material": len(since),
        "changed": sum(item["change_kind"] in {"market-change", "new-evidence", "source-degradation", "stale-evidence"} for item in since),
        "resolved": sum(item["change_kind"] == "resolved" for item in since),
    }
    summary = {
        "visible_count": len(visible),
        "unfiltered_material_count": len(material_items),
        "fetch_refresh_count": sum(item["change_kind"] == "fetch-refresh" for item in all_items),
        "new_count": sum(item["review_state"] == "new" for item in material_items),
        "reviewed_count": sum(item["review_state"] == "reviewed" for item in material_items),
        "acknowledged_count": sum(item["review_state"] == "acknowledged" for item in material_items),
        "snoozed_count": sum(item["review_state"] == "snoozed" for item in material_items),
        "degraded_source_count": sum(item["change_kind"] in {"source-degradation", "stale-evidence"} for item in material_items),
        "provider_call_count": 0,
        "external_delivery": "unavailable",
        "not_financial_advice": True,
    }
    observation_context = public_account_payload(observation_context) if observation_context else {
        "observation_run_version": "watchlist_observation_run.v1",
        "mode": mode,
        "latest_run": {"mode": mode, "status": "not-run", "provider_call_count": 0},
        "active_run": None,
        "changes": [],
        "material_change_count": 0,
        "refresh_action": {"enabled": False, "reason": "no-saved-observation-run"},
        "provider_call_count": 0,
    }
    observation_context["provider_call_count"] = 0
    return {
        "attention_desk_version": ATTENTION_DESK_VERSION,
        "generated_at": current.isoformat(),
        "mode": mode,
        "items": visible,
        "all_items": all_items,
        "digest": _source_digest(visible),
        "since_last_review": since_summary,
        "checkpoint": checkpoint_data,
        "policy": normalized_policy,
        "observation_run": observation_context,
        "filters": {
            "watchlists": sorted({item["subject"]["symbol"] for item in material_items if item["subject"]["symbol"]}),
            "sources": sorted({source["provider"] for item in material_items for source in item["source_register"]}),
            "change_kinds": sorted({item["change_kind"] for item in material_items}),
            "regions": sorted({item["subject"]["region"] for item in material_items if item["subject"]["region"]}),
            "severities": ["info", "material", "high", "critical"],
            "review_states": ["new", "reviewed", "acknowledged", "snoozed"],
        },
        "summary": summary,
        "readiness": {
            "local_review": "available",
            "account_review": "available-when-signed-in",
            "hosted_persistence": "unavailable",
            "external_delivery": "unavailable",
            "gemini_digest": "explicit-opt-in-only",
        },
        "caveat": "Attention rows prioritize stored evidence and source health. They are research information, not a recommendation or urgency claim.",
        "provider_call_count": 0,
        "not_financial_advice": True,
    }


def _extract_payload_sources(
    *,
    watchlist_payload: Any,
    daily_brief_payload: Any,
    news_payload: Any,
    provider_health_payload: Any,
    war_map_payload: Any,
) -> dict[str, Any]:
    watchlist = _record(_unwrap(watchlist_payload))
    brief = _record(_unwrap(daily_brief_payload))
    news = _record(_unwrap(news_payload))
    provider = _unwrap(provider_health_payload)
    war_map = _record(_unwrap(war_map_payload))
    change_inbox = _record(watchlist.get("change_inbox"))
    selected = _record(watchlist.get("selected"))
    catalyst_block = _record(selected.get("catalysts"))
    catalyst_rows = [
        *(_rows(catalyst_block.get("earnings"))),
        *(_rows(catalyst_block.get("dividends"))),
        *(_rows(catalyst_block.get("news"))),
    ]
    news_rows: list[dict[str, Any]] = []
    seen_news: set[str] = set()
    for key in ("high_severity_feed", "event_rows", "normalized_news"):
        for row in _rows(news.get(key)):
            identity = _evidence_identity(row, "news")
            if identity not in seen_news:
                seen_news.add(identity)
                news_rows.append(row)
    war_rows = _rows(war_map.get("event_contexts")) or _rows(war_map.get("markers"))
    return {
        "watchlist_changes": _rows(change_inbox.get("items")),
        "catalysts": catalyst_rows,
        "news_rows": news_rows,
        "daily_brief": brief,
        "provider_health": _rows(provider),
        "war_map_events": war_rows,
    }


def build_attention_desk_from_payloads(
    *,
    watchlist_payload: Any,
    daily_brief_payload: Any,
    news_payload: Any,
    provider_health_payload: Any,
    war_map_payload: Any,
    review_states: dict[str, dict[str, Any]] | None = None,
    policy: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
    observation_run: dict[str, Any] | None = None,
    now: datetime | None = None,
    mode: str = "cache",
) -> dict[str, Any]:
    return build_attention_desk_contract(
        **_extract_payload_sources(
            watchlist_payload=watchlist_payload,
            daily_brief_payload=daily_brief_payload,
            news_payload=news_payload,
            provider_health_payload=provider_health_payload,
            war_map_payload=war_map_payload,
        ),
        review_states=review_states,
        policy=policy,
        checkpoint=checkpoint,
        observation_run=observation_run,
        now=now,
        mode=mode,
    )


def find_forbidden_attention_language(value: Any) -> list[str]:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).lower()
    return [phrase for phrase in _FORBIDDEN_PHRASES if phrase in encoded]


class AttentionReviewStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path

    @staticmethod
    def _fingerprint(value: Any) -> str:
        normalized = _text(value).lower()
        if not _FINGERPRINT_RE.fullmatch(normalized):
            raise ValueError("Attention fingerprint must be a 64-character lowercase SHA-256 value.")
        return normalized

    def _audit(
        self,
        tenant_id: str,
        event_type: str,
        status: str,
        *,
        fingerprint: str = "",
        now: datetime,
        connection: Any | None = None,
    ) -> None:
        def write(target: Any) -> None:
            target.execute(
                "INSERT INTO tenant_attention_audit (event_id, tenant_id, event_type, status, fingerprint, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (new_id("ata"), tenant_id, event_type[:48], status[:32], fingerprint[:64], now.isoformat()),
            )
            target.execute(
                "DELETE FROM tenant_attention_audit WHERE tenant_id=? AND event_id NOT IN (SELECT event_id FROM tenant_attention_audit WHERE tenant_id=? ORDER BY created_at DESC, event_id DESC LIMIT ?)",
                (tenant_id, tenant_id, MAX_AUDIT_ROWS),
            )

        if connection is not None:
            write(connection)
            return
        with get_connection(self.db_path) as target:
            write(target)

    @staticmethod
    def _public_state(row: dict[str, Any], *, now: datetime) -> dict[str, Any]:
        state = _text(row.get("review_state"), "new")
        until = _dt(row.get("snoozed_until"))
        expired = state == "snoozed" and bool(until and until <= now)
        if expired:
            state = _text(row.get("prior_state"), "new")
        return public_account_payload(
            {
                "fingerprint": row.get("fingerprint"),
                "review_state": state,
                "prior_state": row.get("prior_state") or "new",
                "snoozed_until": _iso(row.get("snoozed_until")),
                "snooze_expired": expired,
                "reviewed_at": _iso(row.get("reviewed_at")),
                "acknowledged_at": _iso(row.get("acknowledged_at")),
                "version": int(row.get("version") or 0),
                "updated_at": _iso(row.get("updated_at")),
                "provider_call_count": 0,
            }
        )

    def list_states(
        self,
        context: dict[str, Any],
        fingerprints: Iterable[str],
        *,
        now: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        normalized = []
        for value in list(fingerprints)[:MAX_ATTENTION_ITEMS]:
            fingerprint = self._fingerprint(value)
            if fingerprint not in normalized:
                normalized.append(fingerprint)
        if not normalized:
            return {}
        placeholders = ",".join("?" for _ in normalized)
        rows = execute_query(
            f"SELECT * FROM tenant_attention_states WHERE tenant_id=? AND fingerprint IN ({placeholders})",
            (tenant_id, *normalized),
            fetch=True,
            db_path=self.db_path,
        ) or []
        current = _now(now)
        return {row["fingerprint"]: self._public_state(row, now=current) for row in rows}

    def update_state(
        self,
        context: dict[str, Any],
        fingerprint: str,
        *,
        action: str,
        expected_version: int,
        snoozed_until: datetime | str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        normalized = self._fingerprint(fingerprint)
        if not isinstance(expected_version, int) or expected_version < 0:
            raise ValueError("expected_version must be a non-negative integer.")
        current_time = _now(now)
        with get_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            raw_row = connection.execute(
                "SELECT * FROM tenant_attention_states WHERE tenant_id=? AND fingerprint=?",
                (tenant_id, normalized),
            ).fetchone()
            row = dict(raw_row) if raw_row else None
            current_version = int((row or {}).get("version") or 0)
            if current_version != expected_version:
                raise AttentionConflict(current_version)
            stored_state = _text((row or {}).get("review_state"), "new")
            effective = self._public_state(row or {"fingerprint": normalized}, now=current_time)["review_state"]
            normalized_action = _text(action).lower()
            prior_state = _text((row or {}).get("prior_state"), "new")
            reviewed_at = _iso((row or {}).get("reviewed_at"))
            acknowledged_at = _iso((row or {}).get("acknowledged_at"))
            until = None
            if normalized_action == "review":
                if effective == "acknowledged":
                    raise ValueError("Acknowledged attention cannot move backward to reviewed.")
                new_state = "reviewed"
                reviewed_at = current_time.isoformat()
                prior_state = "reviewed"
            elif normalized_action == "acknowledge":
                new_state = "acknowledged"
                reviewed_at = reviewed_at or current_time.isoformat()
                acknowledged_at = current_time.isoformat()
                prior_state = "acknowledged"
            elif normalized_action == "snooze":
                if effective == "acknowledged":
                    raise ValueError("Acknowledged attention cannot be snoozed.")
                until_dt = _dt(snoozed_until)
                if not until_dt or until_dt <= current_time + timedelta(minutes=4) or until_dt > current_time + timedelta(days=MAX_SNOOZE_DAYS):
                    raise ValueError("Snooze expiry must be between 5 minutes and 30 days.")
                new_state = "snoozed"
                prior_state = effective if effective in {"new", "reviewed"} else "new"
                until = until_dt.isoformat()
            elif normalized_action == "undo-snooze":
                if stored_state != "snoozed":
                    raise ValueError("Only an active or expired snooze can be undone.")
                new_state = prior_state if prior_state in {"new", "reviewed"} else "new"
            else:
                raise ValueError("Attention action must be review, acknowledge, snooze, or undo-snooze.")
            version = current_version + 1
            created_at = _iso((row or {}).get("created_at")) or current_time.isoformat()
            resource_id = _text((row or {}).get("resource_id")) or new_id("att")
            connection.execute(
                """
                INSERT INTO tenant_attention_states (
                    resource_id, tenant_id, owner_user_id, fingerprint, review_state,
                    prior_state, snoozed_until, reviewed_at, acknowledged_at, version,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, fingerprint) DO UPDATE SET
                    owner_user_id=excluded.owner_user_id,
                    review_state=excluded.review_state,
                    prior_state=excluded.prior_state,
                    snoozed_until=excluded.snoozed_until,
                    reviewed_at=excluded.reviewed_at,
                    acknowledged_at=excluded.acknowledged_at,
                    version=excluded.version,
                    updated_at=excluded.updated_at
                """,
                (
                    resource_id,
                    tenant_id,
                    user_id,
                    normalized,
                    new_state,
                    prior_state,
                    until,
                    reviewed_at,
                    acknowledged_at,
                    version,
                    created_at,
                    current_time.isoformat(),
                ),
            )
            self._audit(
                tenant_id,
                f"attention-{normalized_action}",
                new_state,
                fingerprint=normalized,
                now=current_time,
                connection=connection,
            )
        saved = {
            "fingerprint": normalized,
            "review_state": new_state,
            "prior_state": prior_state,
            "snoozed_until": until,
            "reviewed_at": reviewed_at,
            "acknowledged_at": acknowledged_at,
            "version": version,
            "updated_at": current_time.isoformat(),
        }
        return self._public_state(saved, now=current_time)

    def get_policy(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        row = execute_query(
            "SELECT * FROM tenant_attention_policies WHERE tenant_id=?",
            (tenant_id,),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        if not row:
            return _default_policy()
        return validate_attention_policy(
            {
                "minimum_severity": row.get("minimum_severity"),
                "included_change_kinds": json.loads(row.get("included_change_kinds_json") or "[]"),
                "source_health_handling": row.get("source_health_handling"),
                "version": int(row.get("version") or 0),
                "updated_at": row.get("updated_at"),
            }
        )

    def save_policy(
        self,
        context: dict[str, Any],
        policy: dict[str, Any],
        *,
        expected_version: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        validated = validate_attention_policy({**policy, "version": expected_version})
        current = self.get_policy(context)
        if int(current.get("version") or 0) != expected_version:
            raise AttentionConflict(int(current.get("version") or 0))
        timestamp = _now(now).isoformat()
        version = expected_version + 1
        execute_query(
            """
            INSERT INTO tenant_attention_policies (
                resource_id, tenant_id, owner_user_id, minimum_severity,
                included_change_kinds_json, source_health_handling, version,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id) DO UPDATE SET
                owner_user_id=excluded.owner_user_id,
                minimum_severity=excluded.minimum_severity,
                included_change_kinds_json=excluded.included_change_kinds_json,
                source_health_handling=excluded.source_health_handling,
                version=excluded.version,
                updated_at=excluded.updated_at
            """,
            (
                new_id("atp"),
                tenant_id,
                user_id,
                validated["minimum_severity"],
                json.dumps(validated["included_change_kinds"], separators=(",", ":")),
                validated["source_health_handling"],
                version,
                timestamp,
                timestamp,
            ),
            db_path=self.db_path,
        )
        self._audit(tenant_id, "attention-policy", "saved", now=_now(now))
        return self.get_policy(context)

    def get_checkpoint(self, context: dict[str, Any]) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        row = execute_query(
            "SELECT * FROM tenant_attention_checkpoints WHERE tenant_id=?",
            (tenant_id,),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        return public_account_payload(
            {
                "reviewed_through_at": _iso((row or {}).get("reviewed_through_at")),
                "version": int((row or {}).get("version") or 0),
                "updated_at": _iso((row or {}).get("updated_at")),
                "provider_clock_unchanged": True,
            }
        )

    def mark_checkpoint(
        self,
        context: dict[str, Any],
        *,
        expected_version: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        current = self.get_checkpoint(context)
        current_version = int(current.get("version") or 0)
        if current_version != expected_version:
            raise AttentionConflict(current_version)
        timestamp = _now(now).isoformat()
        version = current_version + 1
        execute_query(
            """
            INSERT INTO tenant_attention_checkpoints (
                resource_id, tenant_id, owner_user_id, reviewed_through_at,
                version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id) DO UPDATE SET
                owner_user_id=excluded.owner_user_id,
                reviewed_through_at=excluded.reviewed_through_at,
                version=excluded.version,
                updated_at=excluded.updated_at
            """,
            (new_id("atc"), tenant_id, user_id, timestamp, version, timestamp, timestamp),
            db_path=self.db_path,
        )
        self._audit(tenant_id, "attention-checkpoint", "saved", now=_now(now))
        return self.get_checkpoint(context)

    def list_audit(self, context: dict[str, Any], *, limit: int = 50) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        rows = execute_query(
            "SELECT event_type, status, fingerprint, created_at FROM tenant_attention_audit WHERE tenant_id=? ORDER BY created_at DESC, event_id DESC LIMIT ?",
            (tenant_id, max(1, min(int(limit), MAX_AUDIT_ROWS))),
            fetch=True,
            db_path=self.db_path,
        ) or []
        return [public_account_payload({**row, "provider_call_count": 0}) for row in rows]
