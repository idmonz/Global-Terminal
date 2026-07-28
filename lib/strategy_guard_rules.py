from __future__ import annotations
from typing import Any


def build_guard_result(guard: str, status: str, message: str, severity: str = "watch", evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"guard": guard, "status": status, "message": message, "severity": severity, "evidence": evidence or {}}


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except Exception:
        return default


def data_quality_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    dq = payload.get("data_quality") or payload.get("data_quality_snapshot") or {}
    if not dq:
        return build_guard_result("data_quality_guard", "skipped_no_data", "No data quality snapshot supplied.", "elevated")
    score = _num(dq.get("score") or dq.get("data_quality_score"), None)
    status = str(dq.get("status") or "").lower()
    if score is not None and score < 60:
        return build_guard_result("data_quality_guard", "warning", "Data quality score is below operational review threshold.", "high", dq)
    if status in {"missing", "stale", "proxy", "unavailable"}:
        return build_guard_result("data_quality_guard", "warning", f"Data quality status is {status}.", "high", dq)
    return build_guard_result("data_quality_guard", "passed", "Data quality metadata is present.", "info", dq)


def sample_length_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    sample = _num((payload.get("backtest") or {}).get("sample_size") or payload.get("sample_size"), None)
    if sample is None:
        return build_guard_result("sample_length_guard", "skipped_no_data", "No sample length supplied.", "watch")
    if sample < 100:
        return build_guard_result("sample_length_guard", "warning", "Sample length is thin for robust review.", "elevated", {"sample_size": sample})
    return build_guard_result("sample_length_guard", "passed", "Sample length metadata is acceptable for preliminary review.", "info", {"sample_size": sample})


def missing_data_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    gaps = payload.get("missing_fields") or (payload.get("data_quality") or {}).get("gaps") or []
    if gaps:
        return build_guard_result("missing_data_guard", "warning", "Missing fields or gaps are present.", "elevated", {"gaps": gaps})
    if not payload.get("data_quality"):
        return build_guard_result("missing_data_guard", "skipped_no_data", "No missing-data metadata supplied.", "watch")
    return build_guard_result("missing_data_guard", "passed", "No missing-data gaps were supplied.", "info")


def proxy_dependence_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    proxy_ratio = _num((payload.get("data_quality") or {}).get("proxy_ratio") or payload.get("proxy_ratio"), None)
    if proxy_ratio is None:
        return build_guard_result("proxy_dependence_guard", "skipped_no_data", "No proxy-dependence metadata supplied.", "watch")
    if proxy_ratio > 0.25:
        return build_guard_result("proxy_dependence_guard", "warning", "Proxy dependence is elevated.", "elevated", {"proxy_ratio": proxy_ratio})
    return build_guard_result("proxy_dependence_guard", "passed", "Proxy dependence is within supplied threshold.", "info", {"proxy_ratio": proxy_ratio})


def source_freshness_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    provider = payload.get("provider") or payload.get("provider_snapshot") or {}
    freshness = str(provider.get("freshness") or (payload.get("data_quality") or {}).get("freshness") or "").lower()
    if not freshness:
        return build_guard_result("source_freshness_guard", "skipped_no_data", "No source freshness metadata supplied.", "watch")
    if freshness in {"stale", "missing-key", "missing_key", "unavailable", "historical-only", "historical_only"}:
        return build_guard_result("source_freshness_guard", "warning", f"Source freshness is {freshness}.", "high", provider)
    return build_guard_result("source_freshness_guard", "passed", "Source freshness metadata is acceptable.", "info", provider)


def overfit_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    bt = payload.get("backtest") or {}
    oos = payload.get("oos") or {}
    if not bt or not oos:
        return build_guard_result("overfit_guard", "skipped_no_data", "Backtest/OOS comparison metadata is missing.", "elevated")
    bt_score = _num(bt.get("sharpe") or bt.get("score"), 0)
    oos_score = _num(oos.get("sharpe") or oos.get("score"), 0)
    if bt_score and bt_score - oos_score > 1.0:
        return build_guard_result("overfit_guard", "warning", "Backtest/OOS decay is elevated.", "high", {"backtest": bt_score, "oos": oos_score})
    return build_guard_result("overfit_guard", "passed", "Backtest/OOS decay is not elevated in supplied metadata.", "info")


def lookahead_bias_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    flag = payload.get("lookahead_bias") or (payload.get("backtest") or {}).get("lookahead_bias")
    if flag is None:
        return build_guard_result("lookahead_bias_guard", "skipped_no_data", "No lookahead-bias audit flag supplied.", "elevated")
    return build_guard_result("lookahead_bias_guard", "failed" if flag else "passed", "Lookahead-bias flag is set." if flag else "Lookahead-bias flag is clear.", "critical" if flag else "info")


def survivorship_bias_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    flag = payload.get("survivorship_bias") or (payload.get("backtest") or {}).get("survivorship_bias")
    if flag is None:
        return build_guard_result("survivorship_bias_guard", "skipped_no_data", "No survivorship-bias audit flag supplied.", "watch")
    return build_guard_result("survivorship_bias_guard", "failed" if flag else "passed", "Survivorship-bias flag is set." if flag else "Survivorship-bias flag is clear.", "high" if flag else "info")


def turnover_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    turnover = _num((payload.get("backtest") or {}).get("turnover") or payload.get("turnover"), None)
    if turnover is None:
        return build_guard_result("turnover_guard", "skipped_no_data", "No turnover metadata supplied.", "watch")
    if turnover > 5:
        return build_guard_result("turnover_guard", "warning", "Turnover is elevated in supplied metadata.", "elevated", {"turnover": turnover})
    return build_guard_result("turnover_guard", "passed", "Turnover metadata is within supplied threshold.", "info", {"turnover": turnover})


def drawdown_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    dd = _num((payload.get("backtest") or {}).get("max_drawdown") or payload.get("max_drawdown"), None)
    if dd is None:
        return build_guard_result("drawdown_guard", "skipped_no_data", "No drawdown metadata supplied.", "watch")
    if abs(dd) > 25:
        return build_guard_result("drawdown_guard", "warning", "Drawdown metadata is elevated.", "high", {"max_drawdown": dd})
    return build_guard_result("drawdown_guard", "passed", "Drawdown metadata is within supplied threshold.", "info", {"max_drawdown": dd})


def concentration_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    concentration = _num((payload.get("risk") or {}).get("max_weight") or payload.get("max_weight"), None)
    if concentration is None:
        return build_guard_result("concentration_guard", "skipped_no_data", "No concentration metadata supplied.", "watch")
    if concentration > 0.4:
        return build_guard_result("concentration_guard", "warning", "Concentration metadata is elevated.", "elevated", {"max_weight": concentration})
    return build_guard_result("concentration_guard", "passed", "Concentration metadata is within supplied threshold.", "info")


def leverage_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    leverage = _num((payload.get("risk") or {}).get("leverage") or payload.get("leverage"), None)
    if leverage is None:
        return build_guard_result("leverage_guard", "skipped_no_data", "No leverage metadata supplied.", "watch")
    if leverage > 2:
        return build_guard_result("leverage_guard", "warning", "Leverage metadata is elevated.", "high", {"leverage": leverage})
    return build_guard_result("leverage_guard", "passed", "Leverage metadata is within supplied threshold.", "info")


def no_recommendation_language_guard(payload: dict[str, Any], text: str = "") -> dict[str, Any]:
    blocked = ["should " + "buy", "should " + "sell", "go " + "long", "go " + "short", "time to " + "enter", "time to " + "exit", "trade " + "now"]
    hits = [p for p in blocked if p in (text or "").lower()]
    if hits:
        return build_guard_result("no_recommendation_language_guard", "warning", "Actionable trading phrase detected in research text.", "high", {"hits": hits})
    return build_guard_result("no_recommendation_language_guard", "passed", "No actionable trading phrase detected.", "info")

GUARD_FUNCTIONS = [data_quality_guard, sample_length_guard, missing_data_guard, proxy_dependence_guard, source_freshness_guard, overfit_guard, lookahead_bias_guard, survivorship_bias_guard, turnover_guard, drawdown_guard, concentration_guard, leverage_guard, no_recommendation_language_guard]
