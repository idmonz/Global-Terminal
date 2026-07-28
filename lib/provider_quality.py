from __future__ import annotations

from typing import Any

import pandas as pd

from .provider_registry import build_provider_registry


PROBE_QUALITY_CAVEAT = "Provider quality reflects observed readiness and button-triggered probes. Missing optional feeds are shown as gaps."


STATUS_SCORE = {
    "ok": 100.0,
    "fresh": 100.0,
    "configured": 78.0,
    "free_mode": 72.0,
    "ready_for_optional_probe": 70.0,
    "estimated": 62.0,
    "skipped": 52.0,
    "install_openbb_to_enable": 48.0,
    "optional_key_gap": 42.0,
    "missing_key": 35.0,
    "missing": 30.0,
    "stale": 28.0,
    "error": 5.0,
    "unknown": 25.0,
}


def _frame(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    return pd.DataFrame(value)


def _normalize_status(row: dict[str, Any]) -> str:
    status = str(row.get("status") or row.get("freshness") or "").lower().strip()
    if not status:
        if _truthy(row.get("ok")):
            status = "ok"
        elif _truthy(row.get("skipped")):
            status = "skipped"
        else:
            status = "unknown"
    if _truthy(row.get("skipped")) and status in {"false", "unknown"}:
        status = "skipped"
    return status


def _present(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except Exception:
        pass
    return str(value).strip() != ""


def _truthy(value: Any) -> bool:
    if not _present(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "ok", "available", "configured"}
    return bool(value)


def _score_row(row: dict[str, Any]) -> float:
    status = _normalize_status(row)
    score = STATUS_SCORE.get(status, STATUS_SCORE["unknown"])
    if _truthy(row.get("ok")) and not _truthy(row.get("skipped")):
        score = max(score, 82.0)
    if _present(row.get("error")):
        score = min(score, STATUS_SCORE["error"])
    if _present(row.get("warning")):
        score = min(score, 68.0)
    if _truthy(row.get("requires_key")) and not _truthy(row.get("configured")) and status != "ok":
        score = min(score, STATUS_SCORE["missing_key"])
    if _truthy(row.get("paid_optional")) and not _truthy(row.get("configured")) and status not in {"ok", "fresh"}:
        score = min(score, 55.0)
    return round(float(max(0.0, min(100.0, score))), 1)


def _label(score: float) -> str:
    if score >= 85:
        return "ready"
    if score >= 65:
        return "usable"
    if score >= 40:
        return "limited"
    return "gap"


def _first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except Exception:
            pass
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return "openbb"


def _empty_scorecard() -> pd.DataFrame:
    return pd.DataFrame(columns=["provider", "domain", "status", "quality_score", "quality_label", "configured", "available", "requires_key", "paid_optional", "latency_ms", "warning", "error", "probe_mode", "caveat"])


def build_provider_quality_scorecard(diagnostics: Any = None, registry: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    registry_frame = pd.DataFrame(registry or build_provider_registry())
    diagnostics_frame = _frame(diagnostics)
    if diagnostics_frame.empty:
        diagnostics_frame = registry_frame.rename(columns={"provider_id": "provider"}).copy()
        diagnostics_frame["status"] = diagnostics_frame.apply(
            lambda row: "configured" if bool(row.get("is_configured")) else "missing_key" if bool(row.get("requires_key")) or bool(row.get("env_var")) else "free_mode",
            axis=1,
        )
    if "provider_id" in diagnostics_frame.columns and "provider" not in diagnostics_frame.columns:
        diagnostics_frame = diagnostics_frame.rename(columns={"provider_id": "provider"})
    if "provider" not in diagnostics_frame.columns and "endpoint" in diagnostics_frame.columns:
        diagnostics_frame["provider"] = diagnostics_frame["endpoint"]
    if "provider" not in diagnostics_frame.columns:
        diagnostics_frame["provider"] = diagnostics_frame.index.astype(str)

    registry_lookup = registry_frame.set_index("provider_id").to_dict(orient="index") if not registry_frame.empty and "provider_id" in registry_frame.columns else {}
    rows = []
    for _, row in diagnostics_frame.iterrows():
        record = row.to_dict()
        provider_id = _first_text(record.get("provider"), record.get("source"), record.get("probe"), "unknown")
        registry_row = registry_lookup.get(provider_id, {})
        merged = {**registry_row, **record}
        score = _score_row(merged)
        rows.append(
            {
                "provider": provider_id,
                "domain": merged.get("domain", "runtime probe"),
                "status": _normalize_status(merged),
                "quality_score": score,
                "quality_label": _label(score),
                "configured": _truthy(merged.get("configured", merged.get("is_configured", False))),
                "available": _truthy(merged.get("available", merged.get("is_available", False))),
                "requires_key": _truthy(merged.get("requires_key", False)),
                "paid_optional": _truthy(merged.get("paid_optional", False)),
                "latency_ms": merged.get("latency_ms"),
                "warning": merged.get("warning"),
                "error": merged.get("error"),
                "probe_mode": "real probe" if merged.get("latency_ms") is not None or merged.get("checked_at") else "readiness",
                "caveat": merged.get("caveat") or PROBE_QUALITY_CAVEAT,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return _empty_scorecard()
    return frame.sort_values(["quality_score", "provider"], ascending=[False, True]).reset_index(drop=True)


def build_provider_quality_summary(scorecard: Any) -> dict[str, Any]:
    frame = _frame(scorecard)
    if frame.empty:
        return {
            "provider_count": 0,
            "ready_count": 0,
            "limited_count": 0,
            "gap_count": 0,
            "average_quality": 0.0,
            "summary_label": "unknown",
            "top_gaps": [],
            "caveat": PROBE_QUALITY_CAVEAT,
        }
    scores = pd.to_numeric(frame.get("quality_score"), errors="coerce").fillna(0.0)
    labels = frame.get("quality_label", pd.Series(dtype=str)).astype(str)
    top_gaps = frame[labels.isin(["limited", "gap"])].sort_values("quality_score").head(5)
    average = round(float(scores.mean()), 1)
    return {
        "provider_count": int(len(frame)),
        "ready_count": int((labels == "ready").sum()),
        "limited_count": int((labels == "limited").sum()),
        "gap_count": int((labels == "gap").sum()),
        "average_quality": average,
        "summary_label": "ready" if average >= 80 else "usable" if average >= 60 else "limited" if average >= 40 else "gap",
        "top_gaps": top_gaps[["provider", "status", "warning", "error", "caveat"]].to_dict(orient="records") if not top_gaps.empty else [],
        "caveat": PROBE_QUALITY_CAVEAT,
    }


def build_openbb_probe_quality_table(report: Any) -> pd.DataFrame:
    frame = _frame(report)
    if frame.empty:
        return _empty_scorecard()
    normalized = frame.copy()
    normalized["provider"] = normalized.apply(lambda row: _first_text(row.get("endpoint"), row.get("probe"), "openbb"), axis=1)
    normalized["domain"] = "OpenBB optional backend"
    normalized["requires_key"] = False
    normalized["paid_optional"] = True
    normalized["configured"] = normalized.get("installed", False)
    normalized["available"] = normalized.get("ok", False)
    normalized["status"] = normalized.apply(lambda row: "skipped" if _truthy(row.get("skipped")) else "ok" if _truthy(row.get("ok")) else "error", axis=1)
    return build_provider_quality_scorecard(normalized)
