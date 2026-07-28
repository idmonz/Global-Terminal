from __future__ import annotations

from typing import Any, Iterable

import pandas as pd


EXECUTIVE_CAVEAT = "Executive brief summarizes available evidence only. It is research context, not financial advice."


def _frame(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    return pd.DataFrame(value)


def _status_rows(statuses: Iterable[Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in statuses or []:
        if hasattr(item, "to_dict"):
            rows.append(item.to_dict())
        elif isinstance(item, dict):
            rows.append(item)
    return rows


def _freshness_counts(statuses: Iterable[Any] | None) -> dict[str, int]:
    counts = {"fresh": 0, "estimated": 0, "stale": 0, "missing": 0, "error": 0, "unknown": 0}
    for row in _status_rows(statuses):
        status = str(row.get("status") or row.get("freshness") or "unknown").lower()
        counts[status if status in counts else "unknown"] += 1
    return counts


def _numeric(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if pd.isna(number):
            return default
        return number
    except Exception:
        return default


def _top_abs_moves(cards: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
    if cards.empty or "change_pct" not in cards.columns:
        return []
    frame = cards.copy()
    frame["abs_change"] = pd.to_numeric(frame["change_pct"], errors="coerce").abs()
    frame = frame.sort_values("abs_change", ascending=False).head(limit)
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "label": row.get("label") or row.get("ticker"),
                "ticker": row.get("ticker"),
                "change_pct": row.get("change_pct"),
                "return_1m_pct": row.get("return_1m_pct"),
                "data_status": row.get("data_status", "unknown"),
            }
        )
    return rows


def _data_quality_label(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    if total == 0:
        return "unknown"
    problem = counts.get("missing", 0) + counts.get("error", 0)
    estimated = counts.get("estimated", 0)
    if problem:
        return "gaps visible"
    if estimated >= max(1, total // 2):
        return "proxy heavy"
    if counts.get("stale", 0):
        return "stale watch"
    return "clean"


def build_executive_route_map() -> pd.DataFrame:
    rows = [
        {"desk": "Overview", "page": "app.py", "operator_use": "Cross-asset pulse, source state, and command routing."},
        {"desk": "Financial Terminal", "page": "pages/15_Financial_Terminal.py", "operator_use": "Reported statements, valuation context, availability heatmap."},
        {"desk": "Screener", "page": "pages/13_Screener.py", "operator_use": "Research filters with source confidence and data gaps."},
        {"desk": "War Room", "page": "pages/14_War_Room.py", "operator_use": "OSINT-style event board, map context, provider status."},
        {"desk": "Portfolio Quant Lab", "page": "pages/16_Portfolio_Quant_Lab.py", "operator_use": "Backtests, strategy candidates, factor coverage, OOS checks."},
        {"desk": "Provider Center", "page": "pages/17_Data_Provider_Center.py", "operator_use": "Provider readiness, optional keys, real probe diagnostics."},
        {"desk": "OpenBB Hub", "page": "pages/18_OpenBB_Data_Hub.py", "operator_use": "Optional backend catalog, runtime gaps, button-triggered probes."},
    ]
    return pd.DataFrame(rows)


def build_executive_terminal_brief(
    payload: dict[str, Any] | None,
    overview_status: Any = None,
    *,
    route: str = "Overview Terminal",
    region_focus: str = "Global",
    watchlist_focus: str = "Cross-asset core",
) -> dict[str, Any]:
    payload = payload or {}
    cards = _frame(payload.get("cards"))
    radar = payload.get("market_radar") or {}
    composite = radar.get("composite") or {}
    statuses = payload.get("source_statuses") or []
    counts = _freshness_counts(statuses)
    data_gaps = [str(item) for item in payload.get("data_gaps") or [] if item]
    composite_score = _numeric(composite.get("score"))
    composite_label = str(composite.get("label") or "Mixed evidence")
    movers = _top_abs_moves(cards)
    quality_label = _data_quality_label(counts)

    metrics = [
        {"label": "Composite", "value": composite_score, "delta": composite_label, "freshness": "estimated"},
        {"label": "Fresh Sources", "value": counts["fresh"], "delta": "recent", "freshness": "fresh" if counts["fresh"] else "estimated"},
        {"label": "Proxy / Estimated", "value": counts["estimated"], "delta": "labeled", "freshness": "estimated"},
        {"label": "Data Gaps", "value": len(data_gaps) + counts["missing"] + counts["error"], "delta": quality_label, "freshness": "missing" if data_gaps or counts["missing"] or counts["error"] else "fresh"},
        {"label": "Tracked Assets", "value": len(cards), "delta": watchlist_focus, "freshness": "fresh" if len(cards) else "missing"},
    ]

    cards_payload = [
        {
            "title": "Executive Read",
            "summary": f"{route} is focused on {region_focus}; cross-asset composite is {composite_label} at {composite_score:.1f}.",
            "severity": "medium" if composite_score >= 60 else "watch",
            "tags": ["executive brief", region_focus, watchlist_focus],
            "source": "overview composite",
            "freshness": "estimated",
        },
        {
            "title": "Data Quality",
            "summary": f"Freshness ledger is {quality_label}; {counts['fresh']} fresh, {counts['estimated']} proxy/estimated, {counts['missing']} missing, {counts['error']} error.",
            "severity": "watch" if quality_label != "clean" else "low",
            "tags": ["provider ledger", "transparency"],
            "source": "source statuses",
            "freshness": quality_label if quality_label in {"stale", "missing", "error"} else "estimated",
        },
        {
            "title": "Largest Tape Moves",
            "summary": "; ".join(f"{row['label']} {float(row['change_pct'] or 0):+.2f}%" for row in movers[:4]) if movers else "Move deck is waiting on market data.",
            "severity": "watch",
            "tags": ["market tape", "scan"],
            "source": "cross-asset cards",
            "freshness": "fresh" if movers else "missing",
        },
        {
            "title": "Workflow Links",
            "summary": "Financials, War Room, Provider Center, OpenBB Hub, and Quant Lab now share source-quality language.",
            "severity": "info",
            "tags": ["connected pages", "operator flow"],
            "source": "terminal route map",
            "freshness": "estimated",
        },
    ]

    return {
        "metrics": metrics,
        "cards": cards_payload,
        "movers": pd.DataFrame(movers),
        "freshness_counts": counts,
        "route_map": build_executive_route_map(),
        "overview_status": overview_status.to_dict() if hasattr(overview_status, "to_dict") else overview_status,
        "operator_notes": [
            "Use Provider Center before trusting optional live modules.",
            "Use OpenBB Hub probes only when the optional backend is installed.",
            "Use Quant Lab workbench for historical research and validation checks.",
            "Unavailable fields remain visible as data gaps.",
        ],
        "caveat": EXECUTIVE_CAVEAT,
    }
