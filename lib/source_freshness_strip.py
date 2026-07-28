from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

FRESHNESS_LABELS = [
    "live",
    "fresh",
    "aging",
    "stale",
    "proxy",
    "estimated",
    "historical-only",
    "missing-key",
    "unavailable",
    "low-confidence",
    "inferred",
]

_STATUS_ORDER = {
    "live": 0,
    "fresh": 1,
    "aging": 2,
    "proxy": 3,
    "estimated": 4,
    "historical-only": 5,
    "inferred": 6,
    "low-confidence": 7,
    "missing-key": 8,
    "unavailable": 9,
    "stale": 10,
    "unknown": 11,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_freshness_status(status: str | None = None, *, confidence: str | None = None, missing_key: bool = False) -> str:
    value = str(status or "unknown").strip().lower().replace("_", "-")
    conf = str(confidence or "").strip().lower().replace("_", "-")
    if missing_key:
        return "missing-key"
    if value in FRESHNESS_LABELS:
        return value
    if conf in {"low", "low-confidence"}:
        return "low-confidence"
    if value in {"missing", "no-key", "missing-key"}:
        return "missing-key"
    if value in {"not-available", "disabled", "error"}:
        return "unavailable"
    if value in {"old", "expired"}:
        return "stale"
    return "unknown"


def build_freshness_chip(
    source: str,
    *,
    status: str = "unknown",
    observed_at: str | None = None,
    confidence: str = "unknown",
    caveat: str = "",
    missing_key: bool = False,
    is_inferred: bool = False,
) -> dict[str, Any]:
    normalized = "inferred" if is_inferred else normalize_freshness_status(status, confidence=confidence, missing_key=missing_key)
    return {
        "source": str(source or "Unknown source"),
        "label": normalized,
        "status": normalized,
        "confidence": confidence or "unknown",
        "observed_at": observed_at or "",
        "caveat": caveat or _default_caveat(normalized),
        "sort_order": _STATUS_ORDER.get(normalized, 99),
        "visible": True,
        "research_only": True,
    }


def _default_caveat(status: str) -> str:
    return {
        "live": "Source claims current availability only when provider status confirms it.",
        "fresh": "Recent enough for the current research panel.",
        "aging": "Use with caution; refresh before critical review.",
        "stale": "Outdated source snapshot; refresh or cross-check.",
        "proxy": "Proxy source, not a direct observation.",
        "estimated": "Derived or estimated value; verify method.",
        "historical-only": "Historical dataset only; no current-state claim.",
        "missing-key": "Optional provider key is missing.",
        "unavailable": "Provider or panel is unavailable.",
        "low-confidence": "Low-confidence source; do not treat as confirmed.",
        "inferred": "Inferred from available context and labeled accordingly.",
    }.get(status, "Freshness status is unknown.")


def _chips_from_snapshot(snapshot: Any) -> list[dict[str, Any]]:
    if isinstance(snapshot, list):
        return [
            build_freshness_chip(
                item.get("source") or item.get("provider") or item.get("name") or "source",
                status=item.get("freshness") or item.get("status") or "unknown",
                observed_at=item.get("observed_at") or item.get("created_at") or item.get("timestamp"),
                confidence=item.get("confidence") or item.get("data_confidence") or "unknown",
                caveat=item.get("caveat") or item.get("notes") or "",
                missing_key=bool(item.get("missing_key") or item.get("requires_key") and not item.get("configured", True)),
                is_inferred=bool(item.get("inferred")),
            )
            for item in snapshot
            if isinstance(item, dict)
        ]
    if isinstance(snapshot, dict):
        if "sources" in snapshot and isinstance(snapshot["sources"], list):
            return _chips_from_snapshot(snapshot["sources"])
        if "provider" in snapshot or "source" in snapshot or "freshness" in snapshot or "status" in snapshot:
            return [
                build_freshness_chip(
                    snapshot.get("source") or snapshot.get("provider") or snapshot.get("name") or "source",
                    status=snapshot.get("freshness") or snapshot.get("status") or "unknown",
                    observed_at=snapshot.get("observed_at") or snapshot.get("created_at") or snapshot.get("timestamp"),
                    confidence=snapshot.get("confidence") or snapshot.get("data_confidence") or "unknown",
                    caveat=snapshot.get("caveat") or snapshot.get("notes") or "",
                    missing_key=bool(snapshot.get("missing_key") or snapshot.get("requires_key") and not snapshot.get("configured", True)),
                    is_inferred=bool(snapshot.get("inferred")),
                )
            ]
        return [build_freshness_chip(str(k), status=str(v)) for k, v in snapshot.items() if isinstance(v, str)]
    return []


def build_freshness_strip(snapshot: Any = None, *, title: str = "Source freshness", include_timestamp: bool = True) -> dict[str, Any]:
    chips = _chips_from_snapshot(snapshot)
    if not chips:
        chips = [build_freshness_chip("workspace", status="unavailable", caveat="No source snapshot was supplied.")]
    chips = sorted(chips, key=lambda item: (item["sort_order"], item["source"]))
    worst = chips[-1]["status"] if chips else "unknown"
    return {
        "title": title,
        "chips": chips,
        "worst_status": worst,
        "generated_at": _utc_now() if include_timestamp else "",
        "summary": f"{len(chips)} source chip(s); most conservative status: {worst}",
        "raw_payload_available": True,
        "research_only": True,
    }


def build_source_freshness_strip(snapshot: Any = None, *, title: str = "Source freshness") -> dict[str, Any]:
    return build_freshness_strip(snapshot, title=title)


def build_provider_caveat_chips(provider_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    chips: list[dict[str, Any]] = []
    for row in provider_rows or []:
        missing = bool(row.get("requires_key") and not row.get("is_configured", row.get("configured", False)))
        status = "missing-key" if missing else row.get("freshness") or row.get("status") or "fresh"
        chips.append(
            build_freshness_chip(
                row.get("display_name") or row.get("provider_name") or row.get("provider_id") or "provider",
                status=status,
                confidence=row.get("confidence", "unknown"),
                caveat=row.get("caveat") or row.get("data_quality_notes") or row.get("rate_limit_notes") or "",
                missing_key=missing,
            )
        )
    return chips


def summarize_source_quality(chips_or_snapshot: Any) -> dict[str, Any]:
    chips = chips_or_snapshot if isinstance(chips_or_snapshot, list) else build_freshness_strip(chips_or_snapshot)["chips"]
    counts: dict[str, int] = {}
    for chip in chips:
        counts[chip.get("status", "unknown")] = counts.get(chip.get("status", "unknown"), 0) + 1
    blocking = counts.get("missing-key", 0) + counts.get("unavailable", 0) + counts.get("stale", 0)
    return {"counts": counts, "blocking_caveats": blocking, "research_only": True}
