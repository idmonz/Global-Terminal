from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

VALID_SURFACE_REVIEW_STATUSES = {"new", "reviewed", "requires_review", "archived"}
_NOTICE = "Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_surface_review_item(surface_qa: dict[str, Any], *, case_id: str = "", title: str = "Surface QA Review", status: str | None = None) -> dict[str, Any]:
    anomalies = int(surface_qa.get("anomaly_count", len(surface_qa.get("anomalies", []))) or 0)
    chosen_status = status or ("requires_review" if anomalies else "new")
    if chosen_status not in VALID_SURFACE_REVIEW_STATUSES:
        raise ValueError("invalid_surface_review_status")
    return {
        "ok": True,
        "review_id": f"surface_review_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        "title": title,
        "case_id": case_id,
        "status": chosen_status,
        "created_at": _now(),
        "updated_at": _now(),
        "anomaly_count": anomalies,
        "surface_qa": surface_qa,
        "notice": _NOTICE,
        "research_only": True,
    }


def update_surface_review_status(item: dict[str, Any], status: str, *, notes: str = "") -> dict[str, Any]:
    if status not in VALID_SURFACE_REVIEW_STATUSES:
        raise ValueError("invalid_surface_review_status")
    out = dict(item)
    out.update({"status": status, "review_notes": notes, "updated_at": _now(), "research_only": True})
    if status == "reviewed":
        out["reviewed_at"] = _now()
    return out


def build_surface_review_queue(items: list[dict[str, Any]]) -> dict[str, Any]:
    visible = [item for item in items if item.get("status") != "archived"]
    return {"ok": True, "items": visible, "count": len(visible), "requires_review_count": sum(1 for item in visible if item.get("status") == "requires_review"), "research_only": True}


def build_surface_review_cards(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"review_id": item.get("review_id"), "title": item.get("title"), "status": item.get("status"), "anomaly_count": item.get("anomaly_count", 0), "case_id": item.get("case_id", ""), "research_only": True} for item in items]
